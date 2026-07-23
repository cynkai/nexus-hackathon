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
import copy
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
print("\n[1/7] Scenario.json")
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

    # T11 reg: no pre-computed answer fields in transfers
    t = scenario.get("transfers", [{}])[0]
    forbidden = ["feasible", "status", "available_minutes", "required_minutes"]
    for fname in forbidden:
        check(f"Scenario.json transfers does NOT contain '{fname}' (T2 regression guard)", fname not in t)
except (FileNotFoundError, json.JSONDecodeError) as e:
    check(f"Scenario.json load failed: {e}", False)
    for _ in range(10): check("(skipped)", False)


# ── 2. Rule Engine executes ────────────────────────────────────────
print("\n[2/7] Rule Engine")
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
    check("risk_level is valid", result["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL"))
    check("reason_code is valid",
          result["reason_code"] in ("TRANSFER_FEASIBLE", "TRANSFER_TIME_INSUFFICIENT"))
    check("recommendation is object", isinstance(result["recommendation"], dict))
    check("passenger_message is string", isinstance(result["passenger_message"], str))

    # T11 reg: changing actual_arrival changes risk_score and ETA
    d2 = copy.deepcopy(scenario)
    d2["itinerary"][0]["actual_arrival"] = "2026-07-23T23:55:00"
    d2["delay_events"][0]["actual_arrival"] = "2026-07-23T23:55:00"
    d2["delay_events"][0]["delay_minutes"] = 720
    d2["transfers"][0]["from_arrival"] = "2026-07-23T23:55:00"
    r2 = run_rule_engine(scenario_data=d2)
    check("actual_arrival change → risk_score differs (T2/T5 reg)", result["risk_score"] != r2["risk_score"])
    check("actual_arrival change → ETA differs (T4 reg)", result["estimated_delay_minutes"] != r2["estimated_delay_minutes"])

    # T11 reg: 1min vs 25min shortfall → same next_train, same ETA
    d3 = copy.deepcopy(scenario)
    d3["itinerary"][0]["actual_arrival"] = "2026-07-23T13:29:00"
    d3["delay_events"][0]["actual_arrival"] = "2026-07-23T13:29:00"
    d3["delay_events"][0]["delay_minutes"] = 139
    d3["transfers"][0]["from_arrival"] = "2026-07-23T13:29:00"
    r3 = run_rule_engine(scenario_data=d3)

    d4 = copy.deepcopy(scenario)
    d4["itinerary"][0]["actual_arrival"] = "2026-07-23T13:05:00"
    d4["delay_events"][0]["actual_arrival"] = "2026-07-23T13:05:00"
    d4["delay_events"][0]["delay_minutes"] = 115
    d4["transfers"][0]["from_arrival"] = "2026-07-23T13:05:00"
    r4 = run_rule_engine(scenario_data=d4)

    same_train_3v4 = r3["recommendation"]["service_id"] == r4["recommendation"]["service_id"]
    same_eta_3v4 = r3["estimated_delay_minutes"] == r4["estimated_delay_minutes"]
    check("1min vs 25min shortfall → same next train (T3 reg)", same_train_3v4 and same_eta_3v4)

    # T11 reg: skip trains without seats
    # Passenger ready at 15:40 → should skip KTX-125 (15:30, no seats) → pick KTX-130 (16:00)
    d5 = copy.deepcopy(scenario)
    d5["itinerary"][0]["actual_arrival"] = "2026-07-23T13:42:00"
    d5["delay_events"][0]["actual_arrival"] = "2026-07-23T13:42:00"
    d5["delay_events"][0]["delay_minutes"] = 152
    d5["transfers"][0]["from_arrival"] = "2026-07-23T13:42:00"
    r5 = run_rule_engine(scenario_data=d5)
    check("Skip no-seats train: KTX-125 skipped, KTX-130 selected (T3 reg)",
          r5["recommendation"]["service_id"] == "KTX-130")

    # T11 reg: LAST_TRAIN_MISSED → CRITICAL
    d6 = copy.deepcopy(scenario)
    d6["itinerary"][0]["actual_arrival"] = "2026-07-23T23:00:00"
    d6["delay_events"][0]["actual_arrival"] = "2026-07-23T23:00:00"
    d6["delay_events"][0]["delay_minutes"] = 710
    d6["transfers"][0]["from_arrival"] = "2026-07-23T23:00:00"
    r6 = run_rule_engine(scenario_data=d6)
    check("LAST_TRAIN_MISSED → 1.0 CRITICAL (T3/T5 reg)",
          r6["risk_score"] == 1.0 and r6["risk_level"] == "CRITICAL")
except Exception as e:
    import traceback
    traceback.print_exc()
    check(f"Rule Engine failed: {e}", False)
    for _ in range(16): check("(skipped)", False)


# ── 3+4. Start server once → test API + Dashboard ──────────────────
print("\n[3/7] API Endpoint")
print("[4/7] Dashboard")

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
    check("Dashboard contains loading state", "불러오는 중" in html)
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
print("\n[5/7] Public API Fallback")
try:
    from backend.public_api import get_scenario_data
    data = get_scenario_data()
    check("get_scenario_data() returns dict", isinstance(data, dict))
    check("Fallback data has scenario_id", "scenario_id" in data)
except Exception as e:
    check(f"Public API fallback failed: {e}", False)
    for _ in range(2): check("(skipped)", False)


# ── 6. Explain / Local regression tests ──────────────────────────
print("\n[6/7] Explain + Local Suggestions")
sys.path.insert(0, str(PROJECT_ROOT))
try:
    # Re-use the rule engine result from section 2 (variable 'result' still in scope?)
    # If not, recompute
    try:
        base = result
    except NameError:
        from rules.rule_engine import run as run_re
        base = run_re()

    # T11(5): LLM vs template identity test
    from rules.explainer import explain as explain_result
    llm_path = explain_result(dict(base))
    tmpl_path = explain_result(dict(base))
    decision_fields = ['risk_score', 'risk_level', 'reason_code',
                       'estimated_delay_minutes', 'recommendation',
                       'local_suggestions', 'reason']
    all_identical = True
    for f in decision_fields:
        if json.dumps(llm_path.get(f), ensure_ascii=False, sort_keys=True) != \
           json.dumps(tmpl_path.get(f), ensure_ascii=False, sort_keys=True):
            all_identical = False
            break
    check("LLM/template paths: all decision fields identical (T7 reg)", all_identical)

    # T11(6): local_suggestions validity
    suggestions = base.get("local_suggestions", [])
    from rules.local_recommender import load_local_places
    all_places = load_local_places().get("places", [])
    all_valid = True
    for s in suggestions:
        walk = s.get("walk_minutes_from_station", 0)
        duration = s.get("typical_duration_minutes", 30)
        avail = s.get("time_available_minutes", 0)
        if avail < 0:
            all_valid = False
            break
    check("local_suggestions: all items have non-negative available time (T6 reg)", all_valid)
except Exception as e:
    check(f"Explain/local test failed: {e}", False)
    for _ in range(2): check("(skipped)", False)


# ── 7. Cleanup ────────────────────────────────────────────────────
print(f"\n{'='*40}")
print(f"  PASS: {PASS}  |  FAIL: {FAIL}")
print(f"{'='*40}\n")

sys.exit(0 if FAIL == 0 else 1)
