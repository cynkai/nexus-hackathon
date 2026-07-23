#!/usr/bin/env python3
"""
NEXUS Smoke Test
────────────────
Verifies the complete MVP pipeline is functional.
Exit code: 0 = success, non-zero = failure.
Standard library only.
"""

import json
import http.client
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
PASS = 0
FAIL = 0


def check(description, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {description}")
    else:
        FAIL += 1
        print(f"  ❌ {description}")


# ── 1. Scenario.json exists and is valid ───────────────────────────
print("\n[1/6] Scenario.json")
scenario_path = PROJECT_ROOT / "data" / "Scenario.json"
try:
    with open(scenario_path) as f:
        scenario = json.load(f)
    check("Scenario.json exists and is valid JSON", True)

    required_fields = [
        "scenario_id", "passenger", "route", "itinerary",
        "delay_events", "transfers"
    ]
    for field in required_fields:
        check(f"Scenario.json contains '{field}'", field in scenario)
except (FileNotFoundError, json.JSONDecodeError) as e:
    check(f"Scenario.json load failed: {e}", False)
    for _ in range(6): check("(skipped)", False)


# ── 2. Rule Engine executes ────────────────────────────────────────
print("\n[2/6] Rule Engine")
sys.path.insert(0, str(PROJECT_ROOT))
try:
    from rules.rule_engine import run as run_rule_engine
    result = run_rule_engine()
    check("Rule Engine executes successfully", True)

    required_output = [
        "scenario_id", "transfer_possible", "risk_score",
        "risk_level", "reason_code", "reason",
        "estimated_delay_minutes", "recommendation", "passenger_message"
    ]
    for field in required_output:
        check(f"Rule Engine output contains '{field}'", field in result)

    # Type checks
    check("risk_score is float", isinstance(result["risk_score"], float))
    check("transfer_possible is bool", isinstance(result["transfer_possible"], bool))
    check("risk_level is valid", result["risk_level"] in ("LOW", "MEDIUM", "HIGH"))
    check("reason_code is valid",
          result["reason_code"] in ("TRANSFER_FEASIBLE", "TRANSFER_TIME_INSUFFICIENT"))
    check("recommendation is object", isinstance(result["recommendation"], dict))
    check("passenger_message is string", isinstance(result["passenger_message"], str))
except Exception as e:
    check(f"Rule Engine failed: {e}", False)
    for _ in range(9): check("(skipped)", False)


# ── 3+4. Start server once → test API + Dashboard ──────────────────
print("\n[3/6] API Endpoint")
print("[4/6] Dashboard")

server_proc = None
try:
    import subprocess
    import time
    server_proc = subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / "frontend" / "server.py")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(2)

    conn = http.client.HTTPConnection("localhost", 8080, timeout=5)

    # ── API test ──
    conn.request("GET", "/api/result")
    resp = conn.getresponse()
    api_data = json.loads(resp.read())

    check("/api/result returns HTTP 200", resp.status == 200)
    check("/api/result returns valid JSON", True)
    check("API output has scenario_id", "scenario_id" in api_data)
    check("API output has risk_score", "risk_score" in api_data)
    check("API output has recommendation", "recommendation" in api_data)
    check("API output has passenger_message", "passenger_message" in api_data)

    # ── Dashboard test ──
    conn.request("GET", "/")
    resp = conn.getresponse()
    html = resp.read().decode()
    conn.close()

    check("Dashboard returns HTTP 200", resp.status == 200)
    check("Dashboard contains 'NEXUS Dashboard'", "NEXUS Dashboard" in html)
    check("Dashboard contains loading state", "Loading" in html)
    check("Dashboard does not duplicate rule logic",
          "calculate_risk_score" not in html and
          "generate_recommendation" not in html)
except Exception as e:
    check(f"Server/API/Dashboard failed: {e}", False)
    for _ in range(9): check("(skipped)", False)
finally:
    if server_proc:
        server_proc.terminate()
        server_proc.wait()


# ── 5. Public API fallback ─────────────────────────────────────────
print("\n[5/6] Public API Fallback")
try:
    from backend.public_api import get_scenario_data
    data = get_scenario_data()
    check("get_scenario_data() returns dict", isinstance(data, dict))
    check("Fallback data has scenario_id", "scenario_id" in data)
except Exception as e:
    check(f"Public API fallback failed: {e}", False)
    for _ in range(2): check("(skipped)", False)


# ── 6. Smoke test cleanup ─────────────────────────────────────────
print(f"\n{'='*40}")
print(f"  PASS: {PASS}  |  FAIL: {FAIL}")
print(f"{'='*40}\n")

sys.exit(0 if FAIL == 0 else 1)
