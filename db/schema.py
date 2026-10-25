"""
VitalOptima Relational Schema & ORM Mapping for PostgreSQL
Maps all hospital operational datasets, telemetry, and audit logs to strongly-typed PostgreSQL tables.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, Date, Boolean,
    ForeignKey, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class DepartmentResource(Base):
    """Departmental capacity and resource utilization baseline."""
    __tablename__ = "department_resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(String(50), unique=True, nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    department = Column(String(100), nullable=False, index=True)
    total_capacity = Column(Integer, nullable=False, default=0)
    unavailable_capacity = Column(Integer, nullable=False, default=0)
    occupied_capacity = Column(Integer, nullable=False, default=0)
    available_capacity = Column(Integer, nullable=False, default=0)
    staffed_capacity = Column(Integer, nullable=False, default=0)
    forecast_demand = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<DepartmentResource(resource_id='{self.resource_id}', dept='{self.department}')>"


class HospitalCensusDaily(Base):
    """Historical 365-day inpatient, emergency arrivals, ICU census and admission records."""
    __tablename__ = "hospital_census_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    day_of_week = Column(String(20), nullable=False)
    admissions = Column(Integer, nullable=False, default=0)
    emergency_arrivals = Column(Integer, nullable=False, default=0)
    discharges = Column(Integer, nullable=False, default=0)
    icu_admissions = Column(Integer, nullable=False, default=0)
    elective_admissions = Column(Integer, nullable=False, default=0)
    general_beds_occupied = Column(Integer, nullable=False, default=0)
    icu_beds_occupied = Column(Integer, nullable=False, default=0)
    general_beds_total = Column(Integer, nullable=False, default=300)
    icu_beds_total = Column(Integer, nullable=False, default=30)
    staff_available = Column(Integer, nullable=False, default=0)
    surgeries_scheduled = Column(Integer, nullable=False, default=0)
    average_length_of_stay_days = Column(Float, nullable=False, default=0.0)

    def __repr__(self):
        return f"<HospitalCensusDaily(date='{self.date}', arrivals={self.emergency_arrivals})>"


class StaffingRoster(Base):
    """Clinical nursing and physician schedules, shifts, and staffing constraints."""
    __tablename__ = "staffing_roster"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    shift = Column(String(50), nullable=False, index=True) # Morning, Evening, Night
    department = Column(String(100), nullable=False, index=True)
    staff_role = Column(String(50), nullable=False, index=True) # Registered Nurse, Attending Physician, etc.
    available_count = Column(Integer, nullable=False, default=0)
    required_count = Column(Integer, nullable=False, default=0)
    maximum_permitted_working_hours = Column(Float, nullable=False, default=12.0)
    minimum_rest_hours_between_shifts = Column(Float, nullable=False, default=11.0)

    def __repr__(self):
        return f"<StaffingRoster(date='{self.date}', shift='{self.shift}', dept='{self.department}')>"


class InventorySupply(Base):
    """Critical medical consumables telemetry, daily consumption burn, and restock levels."""
    __tablename__ = "inventory_supplies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    item_id = Column(String(50), nullable=False, index=True)
    item_name = Column(String(150), nullable=False)
    item_category = Column(String(100), nullable=False, index=True)
    opening_stock = Column(Integer, nullable=False, default=0)
    daily_consumption = Column(Integer, nullable=False, default=0)
    incoming_stock = Column(Integer, nullable=False, default=0)
    closing_stock = Column(Integer, nullable=False, default=0)
    reorder_threshold = Column(Integer, nullable=False, default=0)
    supplier_lead_time_days = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<InventorySupply(item_id='{self.item_id}', date='{self.date}', closing={self.closing_stock})>"


class DemandForecastHourly(Base):
    """AI predictive hourly demand forecasts and emergency surge projections."""
    __tablename__ = "demand_forecast_hourly"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hour = Column(String(20), nullable=False)
    hour_index = Column(Integer, nullable=False, unique=True, index=True)
    predicted_demand = Column(Float, nullable=False)
    historical_demand = Column(Float, nullable=False)
    emergency_capacity = Column(Integer, nullable=False)
    available_capacity = Column(Integer, nullable=False)

    def __repr__(self):
        return f"<DemandForecastHourly(hour='{self.hour}', predicted={self.predicted_demand})>"


class DecisionLog(Base):
    """Auditable clinical and administrative resource optimization decisions."""
    __tablename__ = "decision_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    recommendation = Column(Text, nullable=False)
    decision = Column(String(50), nullable=False) # 'Accepted', 'Modified', 'Rejected'
    modified_details = Column(Text, nullable=True)
    administrator = Column(String(100), nullable=False)
    rationale = Column(Text, nullable=True)

    def __repr__(self):
        return f"<DecisionLog(id={self.id}, dec='{self.decision}', admin='{self.administrator}')>"


class SystemAlert(Base):
    """Hospital system alerts, capacity warnings, and critical threshold breaches."""
    __tablename__ = "system_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False) # 'Active', 'Shortage', 'Surge'
    severity = Column(String(50), nullable=False) # 'High', 'Medium', 'Low'
    timestamp = Column(String(50), nullable=False)
    acknowledged = Column(Integer, default=0)

    def __repr__(self):
        return f"<SystemAlert(title='{self.title}', severity='{self.severity}')>"


class RecentActivity(Base):
    """Real-time hospital event timeline and optimization execution log."""
    __tablename__ = "recent_activity"

    id = Column(Integer, primary_key=True, autoincrement=True)
    time_str = Column(String(20), nullable=False)
    title = Column(String(200), nullable=False)
    details = Column(Text, nullable=False)
    color = Column(String(20), nullable=False)

    def __repr__(self):
        return f"<RecentActivity(time='{self.time_str}', title='{self.title}')>"


class ScenarioSimulation(Base):
    """Stress testing scenario results, parameters, and simulated bottleneck forecasts."""
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String(50), nullable=False)
    name = Column(String(150), nullable=False, index=True)
    surge_pct = Column(Float, nullable=False, default=0.0)
    icu_reduction = Column(Integer, nullable=False, default=0)
    staff_loss = Column(Float, nullable=False, default=0.0)
    results_json = Column(Text, nullable=True)

    def __repr__(self):
        return f"<ScenarioSimulation(id={self.id}, name='{self.name}', surge={self.surge_pct}%)>"


class BloodBankInventory(Base):
    """Hospital blood bank backup, component reserves, and transfusion telemetry."""
    __tablename__ = "blood_bank_inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    blood_group = Column(String(50), nullable=False, index=True)
    component_type = Column(String(100), nullable=False, index=True)
    units_available = Column(Integer, nullable=False, default=0)
    units_reserved = Column(Integer, nullable=False, default=0)
    net_available_units = Column(Integer, nullable=False, default=0)
    critical_threshold = Column(Integer, nullable=False, default=0)
    daily_consumption = Column(Float, nullable=False, default=0.0)
    days_of_supply = Column(Float, nullable=False, default=0.0)
    shelf_life_days = Column(Integer, nullable=False, default=0)
    storage_temp = Column(String(50), nullable=False)
    rh_factor = Column(String(20), nullable=False)
    status = Column(String(50), nullable=False)

    def __repr__(self):
        return f"<BloodBankInventory(group='{self.blood_group}', component='{self.component_type}', available={self.units_available})>"


class User(Base):
    """System accounts for RBAC authentication and role management."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False, default="ADMISSION_OFFICER")  # "ADMIN" or "ADMISSION_OFFICER"
    full_name = Column(String(150), nullable=False)
    department = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"


class PatientAdmission(Base):
    """Database-backed hospital patient admission records, bed allocations, and discharge lifecycles."""
    __tablename__ = "patient_admissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admission_id = Column(String(50), unique=True, nullable=False, index=True)
    patient_id = Column(String(50), nullable=False, index=True)
    patient_name = Column(String(150), nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    department = Column(String(100), nullable=False, index=True)
    admission_type = Column(String(50), nullable=False)  # "Emergency", "Elective", "Urgent", "Transfer"
    status = Column(String(50), nullable=False, default="Admitted", index=True)  # "Admitted", "Discharged", "Transferred"
    bed_number = Column(String(50), nullable=True, index=True)
    admitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    discharged_at = Column(DateTime, nullable=True)
    admitted_by = Column(String(100), nullable=False)
    discharged_by = Column(String(100), nullable=True)
    clinical_notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<PatientAdmission(id='{self.admission_id}', patient='{self.patient_name}', bed='{self.bed_number}', status='{self.status}')>"


class AuditLog(Base):
    """Centralized audit trail for security events, admissions, role modifications, and operational actions."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    actor_username = Column(String(100), nullable=False, index=True)
    actor_role = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False, index=True)  # e.g., "admissions.create", "admissions.discharge"
    target_id = Column(String(100), nullable=True)
    target_type = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, default="SUCCESS")  # "SUCCESS", "DENIED", "FAILED"
    details = Column(Text, nullable=True)
    prev_hash = Column(String(64), nullable=True)
    record_hash = Column(String(64), nullable=True)

    def __repr__(self):
        return f"<AuditLog(actor='{self.actor_username}', action='{self.action}', status='{self.status}')>"


class HospitalDataSync(Base):
    """Lightweight cross-user synchronization telemetry tracking table versions and update timestamps."""
    __tablename__ = "hospital_data_sync"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), unique=True, nullable=False, index=True)  # "admissions", "resources"
    version = Column(Integer, default=1, nullable=False)
    last_updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_by = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<HospitalDataSync(entity='{self.entity_type}', version={self.version})>"


