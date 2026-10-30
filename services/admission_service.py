"""
VitalOptima Patient Admission, Resource Allocation & Discharge Service
Provides ACID-compliant patient registration, safe bed allocation with concurrent conflict protection,
idempotency checking, transactional resource recalculation, bed release upon discharge, and cross-user data synchronization telemetry.
"""
import uuid
import secrets
import threading
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Set
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

from config import DB_PATH
from services.auth_service import require_permission, log_audit_event

# Global re-entrant lock to prevent race conditions during concurrent bed allocations in multi-threaded runtime
_ALLOCATION_LOCK = threading.RLock()


def get_sqlite_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def invalidate_caches():
    """Invalidates Streamlit caches to guarantee operational freshness across sessions."""
    try:
        import streamlit as st
        st.cache_data.clear()
    except Exception:
        pass


def bump_sync_version(entity_type: str = "global", actor: str = "system") -> int:
    """Bumps version counter and timestamp in hospital_data_sync for cross-session polling."""
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    new_version = 1

    # SQLite
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM hospital_data_sync WHERE entity_type = ?", (entity_type,))
        row = cursor.fetchone()
        if row:
            new_version = row["version"] + 1
            cursor.execute(
                "UPDATE hospital_data_sync SET version = ?, last_updated_at = ?, updated_by = ? WHERE entity_type = ?",
                (new_version, now_str, actor, entity_type)
            )
        else:
            cursor.execute(
                "INSERT INTO hospital_data_sync (entity_type, version, last_updated_at, updated_by) VALUES (?, ?, ?, ?)",
                (entity_type, 1, now_str, actor)
            )
            new_version = 1
        
        # Also touch 'global'
        if entity_type != "global":
            cursor.execute("""
                UPDATE hospital_data_sync 
                SET version = version + 1, last_updated_at = ?, updated_by = ? 
                WHERE entity_type = 'global'
            """, (now_str, actor))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Sync] Error bumping version in SQLite: {e}")

    # PostgreSQL
    try:
        from db.postgres import get_engine
        from sqlalchemy import text
        engine = get_engine()
        if engine is not None:
            with engine.begin() as pg_conn:
                pg_conn.execute(text("""
                    INSERT INTO hospital_data_sync (entity_type, version, last_updated_at, updated_by)
                    VALUES (:ent, 1, :now_ts, :actor)
                    ON CONFLICT (entity_type) 
                    DO UPDATE SET version = hospital_data_sync.version + 1, last_updated_at = :now_ts, updated_by = :actor;
                """), {"ent": entity_type, "now_ts": datetime.utcnow(), "actor": actor})
    except Exception:
        pass

    invalidate_caches()
    return new_version


def get_sync_status(entity_type: str = "global") -> Dict[str, Any]:
    """Retrieves current sync version and timestamp to allow UI fragments to monitor data freshness."""
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT version, last_updated_at, updated_by FROM hospital_data_sync WHERE entity_type = ?", (entity_type,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "version": row["version"],
                "last_updated_at": row["last_updated_at"],
                "updated_by": row["updated_by"]
            }
    except Exception:
        pass
    return {"version": 1, "last_updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), "updated_by": "system"}


def get_all_departments() -> List[Dict[str, Any]]:
    """Returns list of hospital departments and their bed resource baselines."""
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT resource_id, resource_type, department, total_capacity,
                   unavailable_capacity, occupied_capacity, available_capacity
            FROM department_resources
            ORDER BY department ASC
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        if rows:
            return rows
    except Exception:
        pass
    
    # Fallback to CSV
    csv_path = PROJECT_ROOT / "data" / "department_resources.csv"
    if csv_path.exists():
        import pandas as pd
        df = pd.read_csv(csv_path)
        return df.to_dict(orient="records")
    return []


def get_occupied_bed_numbers(department: Optional[str] = None) -> Set[str]:
    """Returns set of all bed numbers currently assigned to active admissions."""
    occupied = set()
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        if department:
            cursor.execute(
                "SELECT bed_number FROM patient_admissions WHERE status = 'Admitted' AND department = ? AND bed_number IS NOT NULL",
                (department,)
            )
        else:
            cursor.execute(
                "SELECT bed_number FROM patient_admissions WHERE status = 'Admitted' AND bed_number IS NOT NULL"
            )
        for r in cursor.fetchall():
            if r["bed_number"]:
                occupied.add(r["bed_number"].strip().upper())
        conn.close()
    except Exception as e:
        print(f"[AdmissionService] Error fetching occupied beds: {e}")
    return occupied


def get_available_beds_for_department(department: str) -> List[str]:
    """Generates and returns available bed identifiers for a given clinical department."""
    occupied = get_occupied_bed_numbers(department)
    
    # Prefix mapping
    prefixes = {
        "Medicine": "MED",
        "Surgery": "SUR",
        "Orthopedics": "ORT",
        "Pediatrics": "PED",
        "Obstetrics": "OBS",
        "Medical ICU": "MICU",
        "Surgical ICU": "SICU",
        "Main Theatre": "OR-M",
        "Day Surgery": "OR-D",
        "Emergency Theatre": "OR-E",
        "ED Adult": "EDA",
        "ED Pediatric": "EDP",
        "ED Resuscitation": "EDR"
    }
    pfx = prefixes.get(department, department[:4].upper())

    # Get department capacity
    total = 30
    for d in get_all_departments():
        if d["department"].lower() == department.lower():
            total = int(d["total_capacity"])
            break

    available_list = []
    for i in range(1, total + 1):
        bed_id = f"{pfx}-B{i:02d}"
        if bed_id.upper() not in occupied:
            available_list.append(bed_id)
    return available_list


def create_patient_admission(
    patient_id: str,
    patient_name: str,
    department: str,
    admission_type: str,
    age: Optional[int] = None,
    gender: Optional[str] = None,
    bed_number: Optional[str] = None,
    clinical_notes: Optional[str] = None,
    actor_user: Optional[Dict[str, Any]] = None,
    idempotency_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transactionally registers a new patient admission, allocates an available bed,
    updates department resource occupancy, and audits the operation.
    
    Security & Validation:
    - Enforces 'admissions.create' permission on actor_user.
    - Validates all input fields server-side.
    - Prevents concurrent race condition bed assignment using _ALLOCATION_LOCK and SQL checks.
    - Uses ACID transactions; rolls back everything on error.
    - Idempotency check prevents duplicate submissions.
    """
    # 1. Authorization Check (Backend Permission Enforcement)
    require_permission("admissions.create", actor_user)
    actor_username = actor_user.get("username", "system") if actor_user else "system"
    actor_role = actor_user.get("role", "ADMISSION_OFFICER") if actor_user else "ADMISSION_OFFICER"

    # 2. Server-Side Input Validation
    if not patient_id or not str(patient_id).strip():
        raise ValueError("Patient Identifier (MRN / Patient ID) is required.")
    if not patient_name or not str(patient_name).strip():
        raise ValueError("Patient full name is required.")
    if not department or not str(department).strip():
        raise ValueError("Clinical department selection is required.")
    
    valid_types = {"Emergency", "Elective", "Urgent", "Transfer"}
    if admission_type not in valid_types:
        raise ValueError(f"Invalid admission type '{admission_type}'. Must be one of {valid_types}.")

    cleaned_patient_id = str(patient_id).strip().upper()
    cleaned_name = str(patient_name).strip()
    cleaned_dept = str(department).strip()
    cleaned_bed = str(bed_number).strip().upper() if bed_number else None

    # Thread-safe lock protects against simultaneous requests grabbing the same bed
    with _ALLOCATION_LOCK:
        conn = get_sqlite_conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()

            # 3. Idempotency Check (Prevent duplicate submission)
            if idempotency_key:
                cursor.execute(
                    "SELECT admission_id FROM patient_admissions WHERE admission_id = ?",
                    (idempotency_key,)
                )
                if cursor.fetchone():
                    conn.rollback()
                    conn.close()
                    raise ValueError(f"Admission request '{idempotency_key}' was already processed.")

            # Check if patient already has an active admission in hospital
            cursor.execute(
                "SELECT admission_id, department, bed_number FROM patient_admissions WHERE patient_id = ? AND status = 'Admitted'",
                (cleaned_patient_id,)
            )
            active_existing = cursor.fetchone()
            if active_existing:
                conn.rollback()
                conn.close()
                raise ValueError(
                    f"Patient {cleaned_patient_id} already has an active admission ({active_existing['admission_id']}) in {active_existing['department']} (Bed: {active_existing['bed_number']})."
                )

            # 4. Department & Bed Verification
            cursor.execute(
                "SELECT * FROM department_resources WHERE LOWER(department) = LOWER(?)",
                (cleaned_dept,)
            )
            dept_row = cursor.fetchone()
            if not dept_row:
                conn.rollback()
                conn.close()
                raise ValueError(f"Department '{cleaned_dept}' does not exist in hospital resource registry.")

            avail_cap = dept_row["available_capacity"]
            occ_cap = dept_row["occupied_capacity"]
            tot_cap = dept_row["total_capacity"]
            unavail_cap = dept_row["unavailable_capacity"]

            if avail_cap <= 0:
                conn.rollback()
                conn.close()
                raise ValueError(f"Department '{cleaned_dept}' has 0 available beds. Current capacity fully saturated.")

            # If bed number specified, check availability
            if cleaned_bed:
                cursor.execute(
                    "SELECT admission_id, patient_name FROM patient_admissions WHERE UPPER(bed_number) = ? AND status = 'Admitted'",
                    (cleaned_bed,)
                )
                bed_conflict = cursor.fetchone()
                if bed_conflict:
                    conn.rollback()
                    conn.close()
                    raise ValueError(
                        f"Bed '{cleaned_bed}' is already occupied by active patient '{bed_conflict['patient_name']}' ({bed_conflict['admission_id']})."
                    )

            # 5. Generate Unique Admission ID
            today_str = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            rand_suffix = secrets.token_hex(4).upper()
            admission_id = idempotency_key or f"ADM-{today_str}-{rand_suffix}"
            now_ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

            # 6. Insert Admission Record
            cursor.execute("""
                INSERT INTO patient_admissions (
                    admission_id, patient_id, patient_name, age, gender, department,
                    admission_type, status, bed_number, admitted_at, discharged_at,
                    admitted_by, discharged_by, clinical_notes, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                admission_id, cleaned_patient_id, cleaned_name, age, gender, cleaned_dept,
                admission_type, "Admitted", cleaned_bed, now_ts, None,
                actor_username, None, clinical_notes or "", now_ts
            ))

            # 7. Update Department Resource Capacities (Authoritative recalculation)
            new_occupied = occ_cap + 1
            new_available = max(0, tot_cap - unavail_cap - new_occupied)
            cursor.execute("""
                UPDATE department_resources
                SET occupied_capacity = ?, available_capacity = ?, updated_at = ?
                WHERE id = ?
            """, (new_occupied, new_available, now_ts, dept_row["id"]))

            # Commit Transaction
            conn.commit()
            conn.close()

            # 8. Record Immutable Audit Event
            log_audit_event(
                actor_username=actor_username,
                actor_role=actor_role,
                action="admissions.create",
                target_id=admission_id,
                target_type="admission",
                status="SUCCESS",
                details=f"Admitted patient {cleaned_name} ({cleaned_patient_id}) to {cleaned_dept}, Bed: {cleaned_bed or 'Unassigned'}"
            )

            # 9. Trigger Cross-User Data Sync & Outbox Journaling
            bump_sync_version("admissions", actor=actor_username)
            bump_sync_version("resources", actor=actor_username)
            try:
                from db.database import record_sync_outbox, sync_pending_outbox
                record_sync_outbox(
                    entity_type="admissions",
                    entity_id=admission_id,
                    operation="INSERT",
                    payload={
                        "admission_id": admission_id,
                        "patient_id": cleaned_patient_id,
                        "patient_name": cleaned_name,
                        "age": age,
                        "gender": gender,
                        "department": cleaned_dept,
                        "admission_type": admission_type,
                        "status": "Admitted",
                        "bed_number": cleaned_bed,
                        "admitted_at": now_ts,
                        "admitted_by": actor_username,
                        "clinical_notes": clinical_notes or ""
                    }
                )
                sync_pending_outbox()
            except Exception as e_outbox:
                print(f"[AdmissionService] Outbox sync notice: {e_outbox}")

            return {
                "success": True,
                "admission_id": admission_id,
                "patient_id": cleaned_patient_id,
                "patient_name": cleaned_name,
                "department": cleaned_dept,
                "bed_number": cleaned_bed,
                "status": "Admitted",
                "admitted_at": now_ts,
                "updated_department_capacity": {
                    "total": tot_cap,
                    "occupied": new_occupied,
                    "available": new_available
                }
            }

        except sqlite3.IntegrityError as e:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
            err_msg = str(e)
            if "idx_active_bed_occupancy" in err_msg or "UNIQUE constraint failed" in err_msg:
                user_msg = f"Bed '{cleaned_bed}' was just claimed by a concurrent admission request. Please select another available bed."
            else:
                user_msg = f"Database integrity violation during admission: {err_msg}"
            log_audit_event(
                actor_username=actor_username,
                actor_role=actor_role,
                action="admissions.create",
                target_id=cleaned_patient_id,
                target_type="patient",
                status="CONFLICT",
                details=user_msg
            )
            raise ValueError(user_msg) from e
        except Exception as e:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
            log_audit_event(
                actor_username=actor_username,
                actor_role=actor_role,
                action="admissions.create",
                target_id=cleaned_patient_id,
                target_type="patient",
                status="FAILED",
                details=f"Admission failed: {str(e)}"
            )
            raise e


def discharge_patient(
    admission_id: str,
    discharge_notes: Optional[str] = None,
    actor_user: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Transactionally discharges a patient, releases their allocated bed,
    recalculates department resource availability, and records the audit trail.
    
    Security & Validation:
    - Enforces 'admissions.discharge' permission on actor_user.
    - Prevents double-discharge of already discharged patients.
    - Preserves historical records (does not delete).
    """
    require_permission("admissions.discharge", actor_user)
    actor_username = actor_user.get("username", "system") if actor_user else "system"
    actor_role = actor_user.get("role", "ADMISSION_OFFICER") if actor_user else "ADMISSION_OFFICER"

    if not admission_id:
        raise ValueError("Admission ID is required to process discharge.")

    with _ALLOCATION_LOCK:
        conn = get_sqlite_conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM patient_admissions WHERE admission_id = ?", (admission_id,))
            admission = cursor.fetchone()
            if not admission:
                conn.rollback()
                conn.close()
                raise ValueError(f"Admission record '{admission_id}' not found.")

            if admission["status"] == "Discharged":
                conn.rollback()
                conn.close()
                raise ValueError(f"Admission '{admission_id}' is already discharged on {admission['discharged_at']}.")

            now_ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            dept_name = admission["department"]
            bed_num = admission["bed_number"]

            # Update admission record to Discharged
            cursor.execute("""
                UPDATE patient_admissions
                SET status = 'Discharged', discharged_at = ?, discharged_by = ?,
                    clinical_notes = clinical_notes || ?, updated_at = ?
                WHERE admission_id = ?
            """, (
                now_ts, actor_username,
                f"\n[Discharge Summary {now_ts}]: {discharge_notes}" if discharge_notes else "",
                now_ts, admission_id
            ))

            # Update Department Resource Capacities (Release 1 occupied bed)
            cursor.execute(
                "SELECT * FROM department_resources WHERE LOWER(department) = LOWER(?)",
                (dept_name,)
            )
            dept_row = cursor.fetchone()
            if dept_row:
                new_occ = max(0, dept_row["occupied_capacity"] - 1)
                new_avail = max(0, dept_row["total_capacity"] - dept_row["unavailable_capacity"] - new_occ)
                cursor.execute("""
                    UPDATE department_resources
                    SET occupied_capacity = ?, available_capacity = ?, updated_at = ?
                    WHERE id = ?
                """, (new_occ, new_avail, now_ts, dept_row["id"]))

            conn.commit()
            conn.close()

            # Record Audit Event
            log_audit_event(
                actor_username=actor_username,
                actor_role=actor_role,
                action="admissions.discharge",
                target_id=admission_id,
                target_type="admission",
                status="SUCCESS",
                details=f"Discharged patient {admission['patient_name']} from {dept_name}. Bed {bed_num} released."
            )

            # Trigger Data Sync & Outbox Journaling
            bump_sync_version("admissions", actor=actor_username)
            bump_sync_version("resources", actor=actor_username)
            try:
                from db.database import record_sync_outbox, sync_pending_outbox
                record_sync_outbox(
                    entity_type="admissions",
                    entity_id=admission_id,
                    operation="UPDATE",
                    payload={
                        "admission_id": admission_id,
                        "status": "Discharged",
                        "discharged_at": now_ts,
                        "discharged_by": actor_username,
                        "discharge_notes": discharge_notes or ""
                    }
                )
                sync_pending_outbox()
            except Exception as e_outbox:
                print(f"[AdmissionService] Outbox sync notice: {e_outbox}")

            return {
                "success": True,
                "admission_id": admission_id,
                "patient_name": admission["patient_name"],
                "department": dept_name,
                "released_bed": bed_num,
                "discharged_at": now_ts
            }

        except Exception as e:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
            log_audit_event(
                actor_username=actor_username,
                actor_role=actor_role,
                action="admissions.discharge",
                target_id=admission_id,
                target_type="admission",
                status="FAILED",
                details=f"Discharge failed: {str(e)}"
            )
            raise e


def get_active_admissions(department_filter: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    """Retrieves all currently admitted patients for clinical rosters and admission workspaces."""
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        if department_filter and department_filter != "All Departments":
            cursor.execute("""
                SELECT * FROM patient_admissions
                WHERE status = 'Admitted' AND department = ?
                ORDER BY admitted_at DESC LIMIT ?
            """, (department_filter, limit))
        else:
            cursor.execute("""
                SELECT * FROM patient_admissions
                WHERE status = 'Admitted'
                ORDER BY admitted_at DESC LIMIT ?
            """, (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"[AdmissionService] Error fetching active admissions: {e}")
        return []


def get_all_admission_history(limit: int = 200) -> List[Dict[str, Any]]:
    """Retrieves all historical admission and discharge records."""
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patient_admissions ORDER BY admitted_at DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"[AdmissionService] Error fetching admission history: {e}")
        return []


def get_live_bed_metrics() -> Dict[str, Any]:
    """
    Computes live, authoritative hospital-wide bed occupancy and capacity metrics
    directly from database department_resources table.
    Ensures that whenever admissions or discharges occur, metrics immediately reflect actual counts.
    """
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM department_resources")
        dept_rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
    except Exception:
        dept_rows = []

    if not dept_rows:
        # Fallback to config baseline
        from config import (
            GENERAL_BEDS_TOTAL, GENERAL_BEDS_OCCUPIED, GENERAL_BEDS_AVAILABLE, GENERAL_BEDS_RATE,
            ICU_BEDS_TOTAL, ICU_BEDS_OCCUPIED, ICU_BEDS_AVAILABLE, ICU_BEDS_RATE
        )
        return {
            "general_total": GENERAL_BEDS_TOTAL,
            "general_occupied": GENERAL_BEDS_OCCUPIED,
            "general_available": GENERAL_BEDS_AVAILABLE,
            "general_rate": GENERAL_BEDS_RATE,
            "icu_total": ICU_BEDS_TOTAL,
            "icu_occupied": ICU_BEDS_OCCUPIED,
            "icu_available": ICU_BEDS_AVAILABLE,
            "icu_rate": ICU_BEDS_RATE,
            "sync_version": 1,
            "last_updated": datetime.utcnow().strftime("%H:%M:%S")
        }

    gen_total = 0
    gen_occ = 0
    gen_avail = 0
    icu_total = 0
    icu_occ = 0
    icu_avail = 0

    for d in dept_rows:
        rtype = d.get("resource_type", "")
        tot = int(d.get("total_capacity", 0))
        occ = int(d.get("occupied_capacity", 0))
        avail = int(d.get("available_capacity", 0))

        if "General Bed" in rtype:
            gen_total += tot
            gen_occ += occ
            gen_avail += avail
        elif "ICU Bed" in rtype:
            icu_total += tot
            icu_occ += occ
            icu_avail += avail

    gen_rate = round((gen_occ / gen_total * 100), 1) if gen_total > 0 else 0.0
    icu_rate = round((icu_occ / icu_total * 100), 1) if icu_total > 0 else 0.0

    sync = get_sync_status("global")

    return {
        "general_total": gen_total,
        "general_occupied": gen_occ,
        "general_available": gen_avail,
        "general_rate": gen_rate,
        "icu_total": icu_total,
        "icu_occupied": icu_occ,
        "icu_available": icu_avail,
        "icu_rate": icu_rate,
        "sync_version": sync.get("version", 1),
        "last_updated": sync.get("last_updated_at", "")
    }
