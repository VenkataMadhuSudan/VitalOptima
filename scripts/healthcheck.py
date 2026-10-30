#!/usr/bin/env python3
"""
VitalOptima Container & Application Healthcheck CLI Probe
Probes local Streamlit application server endpoint and database engine.
Returns exit code 0 if fully operational, 1 if unhealthy or degraded.
"""
import sys
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.db_readiness import check_db_readiness


def check_app_health(port: int = 8501, timeout: float = 5.0) -> dict:
    health_url = f"http://localhost:{port}/_stcore/health"
    result = {
        "status": "HEALTHY",
        "app_endpoint": health_url,
        "http_ok": False,
        "db_ok": False,
        "details": {}
    }

    # 1. Probe HTTP Streamlit health endpoint
    try:
        req = urllib.request.Request(health_url, headers={"User-Agent": "VitalOptima-HealthProbe/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result["http_ok"] = response.status == 200
            result["details"]["http_status"] = response.status
    except Exception as e:
        result["http_ok"] = False
        result["details"]["http_error"] = str(e)

    # 2. Probe Database Readiness
    db_res = check_db_readiness(timeout_sec=timeout)
    result["db_ok"] = db_res.get("status") == "READY"
    result["details"]["db_status"] = db_res.get("status")
    result["details"]["db_latency_ms"] = db_res.get("total_check_time_ms")

    # Overall liveness: both HTTP and DB must be functional
    if not (result["http_ok"] and result["db_ok"]):
        result["status"] = "UNHEALTHY"

    return result


def main():
    parser = argparse.ArgumentParser(description="VitalOptima System Healthcheck Probe")
    parser.add_argument("--port", type=int, default=8501, help="Streamlit port")
    parser.add_argument("--timeout", type=float, default=5.0, help="Probe timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--db-only", action="store_true", help="Probe database engine only")
    args = parser.parse_args()

    if args.db_only:
        db_res = check_db_readiness(timeout_sec=args.timeout)
        if args.json:
            print(json.dumps(db_res, indent=2))
        else:
            print(f"Database: {db_res['status']}")
        sys.exit(0 if db_res["status"] == "READY" else 1)

    result = check_app_health(port=args.port, timeout=args.timeout)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status_tag = "[OK]" if result["status"] == "HEALTHY" else "[WARN]"
        print(f"{status_tag} System Status: {result['status']}")
        print(f"  - HTTP Health Endpoint: {'UP' if result['http_ok'] else 'DOWN'}")
        print(f"  - Database Engine: {'READY' if result['db_ok'] else 'FAILED'}")

    sys.exit(0 if result["status"] == "HEALTHY" else 1)


if __name__ == "__main__":
    main()

