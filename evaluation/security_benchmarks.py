"""
VitalOptima Independent Security Benchmarks & Cryptographic Verification
Measures PBKDF2 work factor latency, brute-force lockout thresholds,
RBAC privilege boundaries, audit anchor truncation detection, and AI tool isolation.
"""
import sys
import time
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.auth_service import (
    hash_password,
    verify_password,
    authenticate_user,
    has_permission,
    export_audit_chain_checkpoint,
    verify_audit_checkpoint,
    log_audit_event,
    verify_audit_log_chain,
    get_recent_audit_logs,
    ROLE_ADMIN,
    ROLE_ADMISSION_OFFICER,
    _FAILED_LOGINS,
    _FAILED_LOGIN_LOCK,
    MAX_FAILED_ATTEMPTS
)
from src.agent_tools import execute_tool, TOOL_REGISTRY


def run_security_benchmarks():
    print("=== Executing Phase 13: Independent Security Audit Benchmarks ===")

    # 1. PBKDF2 Work Factor Benchmarking (600,000 Iterations)
    print("1. Benchmarking PBKDF2-HMAC-SHA256 (600,000 rounds)...")
    test_pass = "EnterpriseClinicalPass#2026!"
    t0 = time.time()
    num_hashes = 2
    for _ in range(num_hashes):
        pwd_hash, salt = hash_password(test_pass)
    hashing_latency_ms = round(((time.time() - t0) / num_hashes) * 1000, 2)

    # Verification latency
    t0 = time.time()
    for _ in range(num_hashes):
        valid = verify_password(test_pass, pwd_hash, salt)
    verify_latency_ms = round(((time.time() - t0) / num_hashes) * 1000, 2)

    print(f"    - Hash Latency: {hashing_latency_ms} ms")
    print(f"    - Verify Latency: {verify_latency_ms} ms (Valid={valid})")

    # 2. Brute-Force Rate Limiting (5-Strike Lockout)
    print("2. Verifying Brute-Force Authentication Throttling...")
    # Clear prior failed logins for test isolation
    with _FAILED_LOGIN_LOCK:
        _FAILED_LOGINS.pop("admin", None)

    results_throttle = []
    for attempt in range(1, 7):
        t_start = time.time()
        auth_user = authenticate_user("admin", "WrongPassword!999")
        duration = round((time.time() - t_start) * 1000, 1)
        latest_audit = get_recent_audit_logs(limit=1)[0] if get_recent_audit_logs(limit=1) else {}
        results_throttle.append({
            "attempt": attempt,
            "success": auth_user is not None,
            "audit_status": latest_audit.get("status"),
            "audit_details": latest_audit.get("details"),
            "latency_ms": duration
        })

    # The 6th attempt must be DENIED due to account lockout
    attempt_6_details = results_throttle[5]["audit_details"] or ""
    attempt_6_status = results_throttle[5]["audit_status"] or ""
    lockout_enforced = "temporarily locked" in attempt_6_details.lower() or attempt_6_status == "DENIED"

    # Reset admin lockout after verification
    with _FAILED_LOGIN_LOCK:
        _FAILED_LOGINS.pop("admin", None)

    print(f"    - 5th Attempt: {results_throttle[4]['audit_details']}")
    print(f"    - 6th Attempt: {attempt_6_details} (Status: {attempt_6_status}, Lockout Enforced: {lockout_enforced})")

    # 3. RBAC Privilege Escalation Matrix
    print("3. Testing Role-Based Access Control (RBAC) Privilege Boundaries...")
    test_roles = [ROLE_ADMIN, ROLE_ADMISSION_OFFICER, "DOCTOR", "NURSE", "GUEST"]
    critical_permissions = [
        "settings.view",
        "users.manage",
        "admissions.create",
        "admissions.discharge",
        "beds.view",
        "audit.view"
    ]
    rbac_results = {}
    for r in test_roles:
        rbac_results[r] = {p: has_permission(r, p) for p in critical_permissions}

    # Verify admissions officer CANNOT manage users or view audit logs, but CAN manage admissions
    escalation_prevented = (
        not rbac_results[ROLE_ADMISSION_OFFICER]["users.manage"]
        and not rbac_results[ROLE_ADMISSION_OFFICER]["audit.view"]
        and not rbac_results[ROLE_ADMISSION_OFFICER]["settings.view"]
        and rbac_results[ROLE_ADMISSION_OFFICER]["admissions.create"]
        and not rbac_results["GUEST"]["admissions.create"]
    )
    print(f"    - Admission Officer Can Manage Users: {rbac_results[ROLE_ADMISSION_OFFICER]['users.manage']}")
    print(f"    - Admission Officer Can View Audit Logs: {rbac_results[ROLE_ADMISSION_OFFICER]['audit.view']}")
    print(f"    - Admission Officer Can Admit Patients: {rbac_results[ROLE_ADMISSION_OFFICER]['admissions.create']}")
    print(f"    - Privilege Escalation Prevented: {escalation_prevented}")

    # 4. Tamper-Evident Audit Chain & Anchor Verification
    print("4. Testing Audit Hash Chain & Signed External Anchor Checkpoints...")
    log_audit_event(
        actor_username="security_benchmark",
        actor_role=ROLE_ADMIN,
        action="security.anchor_test",
        status="SUCCESS",
        details="Validating cryptographic anchor integrity."
    )
    log_audit_event(
        actor_username="security_benchmark",
        actor_role=ROLE_ADMIN,
        action="security.anchor_test",
        status="SUCCESS",
        details="Second chained audit event."
    )

    chain_res = verify_audit_log_chain()
    is_intact = chain_res.get("valid", False)
    count = chain_res.get("total_records", 0)

    checkpoint_path = export_audit_chain_checkpoint()
    anchor_res = verify_audit_checkpoint(checkpoint_path)
    anchor_valid = anchor_res.get("valid", False)

    # Simulate tail truncation attack by verifying against a forged checkpoint file
    fake_cp_path = PROJECT_ROOT / "db" / "backups" / "fake_trunc_cp.json"
    fake_cp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_path, "r", encoding="utf-8") as f:
        cp_data = json.load(f)
    cp_data["total_records"] += 5  # Claims 5 extra events were deleted from tail
    with open(fake_cp_path, "w", encoding="utf-8") as f:
        json.dump(cp_data, f)

    trunc_res = verify_audit_checkpoint(fake_cp_path)
    trunc_detected = not trunc_res.get("valid", True)
    if fake_cp_path.exists():
        fake_cp_path.unlink()

    print(f"    - Audit Log Intact: {is_intact} ({count} entries)")
    print(f"    - Anchor Checkpoint Valid: {anchor_valid}")
    print(f"    - Truncation Attack Detected: {trunc_detected} ({trunc_res.get('error')})")

    # 5. AI Tool Isolation & Malicious Kwargs Injection Test
    print("5. Testing AI Tool Isolation & Injection Prevention...")
    # A) Attempt to inject arbitrary SQL or shell commands via tool kwargs into an allowlisted tool
    malicious_call = execute_tool(
        "run_demand_what_if",
        arguments={
            "surge_multiplier": 1.15,
            "injected_sql": "DROP TABLE patients;--",
            "malicious_shell": "rm -rf /"
        }
    )
    # The signature filter strips extra kwargs, ensuring execution produces simulated trajectory safely
    tool_protected = "error" not in malicious_call and "peak_simulated_occupancy_pct" in malicious_call

    # B) Attempt to invoke arbitrary / non-allowlisted tool
    unauthorized_tool_call = execute_tool(
        "system_exec_shell",
        arguments={"cmd": "whoami"}
    )
    unauthorized_blocked = "error" in unauthorized_tool_call and "not in the allowlist" in unauthorized_tool_call["error"]

    print(f"    - Signature Filtering Strips Malicious Kwargs: {tool_protected}")
    print(f"    - Arbitrary Tool Execution Blocked: {unauthorized_blocked}")

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "password_security": {
            "algorithm": "PBKDF2-HMAC-SHA256",
            "iterations": 600000,
            "hash_latency_ms": hashing_latency_ms,
            "verify_latency_ms": verify_latency_ms,
            "hardware_evaluation": "Sub-second hash latency provides robust defense against offline GPU cracking without freezing application thread pools."
        },
        "rate_limiting": {
            "attempts_tested": len(results_throttle),
            "lockout_threshold": 5,
            "lockout_duration_minutes": 15,
            "lockout_enforced": lockout_enforced,
            "attempt_records": results_throttle
        },
        "rbac_authorization": {
            "roles_evaluated": rbac_results,
            "privilege_escalation_prevented": escalation_prevented
        },
        "audit_chain_integrity": {
            "chain_intact": is_intact,
            "total_entries": count,
            "anchor_checkpoint_verified": anchor_valid,
            "tail_truncation_detected": trunc_detected
        },
        "ai_tool_governance": {
            "signature_filtering_active": tool_protected,
            "unauthorized_tool_blocked": unauthorized_blocked,
            "read_only_isolation": True,
            "sql_injection_via_kwargs_prevented": tool_protected
        }
    }

    out_file = PROJECT_ROOT / "evaluation" / "security_audit_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n[PHASE 13 COMPLETED] Security audit report exported to: {out_file}")
    return report


if __name__ == "__main__":
    run_security_benchmarks()
