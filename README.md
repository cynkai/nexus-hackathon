# NEXUS — Rail + Aviation Transfer Predictor

> l내일路(로) 해커톤 2026

**NEXUS** demonstrates why combining railway and aviation data enables better transfer decisions than treating each system independently.

---

## Problem

Railway and aviation systems optimize independently. Transfer decisions across both systems remain disconnected. When a flight is delayed, a passenger has no way to know whether their scheduled train transfer is still feasible — and if not, what to do next.

## Solution

NEXUS integrates rail and aviation schedule data in real time:

1. **Detect** delay events from flight data
2. **Calculate** transfer feasibility using deterministic rules
3. **Score** the travel risk
4. **Generate** explainable recommendations
5. **Display** results via Operator Dashboard + Passenger View

---

## Architecture

```
data/Scenario.json  ─┐
                     ├──→ backend/public_api.py ─→ rules/rule_engine.py ─→ frontend/server.py ─→ frontend/index.html
Public API (future) ─┘         │                        │                       │
                          normalizer              deterministic rules        Dashboard UI
                          (optional)              (no ML, no LLM)           (presentation only)
```

**Data flow:**

```
Scenario.json
    ↓
Rule Engine (read-only facts)
    ↓
/api/result (JSON contract)
    ↓
Dashboard (Operator + Passenger View)
```

## Key design decisions

| Decision | Rationale |
|----------|-----------|
| Rule-based (no ML/LLM) | Deterministic, explainable, demo-reliable |
| Facts vs. judgment separated | Scenario is facts only; Rule Engine judges; Dashboard presents |
| Public API is optional | Demo always works; API integration is additive |
| No framework in frontend | Stdlib only, zero dependencies, single file |
| Output contract frozen | Dashboard never needs changes when data source changes |

---

## Repository Structure

```
nexus-hackathon/
├── AGENTS.md                  AI agent behavior rules
├── PROJECT_CHARTER.md         Project mission and constraints
├── TASKS.md                   Task breakdown
├── README.md                  ← You are here
├── JUDGE.md                   Judges' one-pager
├── backend/
│   ├── __init__.py
│   └── public_api.py          Optional public data source + normalizer
├── data/
│   └── Scenario.json          Mock schedule data (single source of truth)
├── docs/
│   ├── DEMO_CHECKLIST.md      Demo preparation checklist
│   └── Scenario.md            Human-readable scenario definition
├── frontend/
│   ├── index.html             Dashboard + Passenger View UI
│   └── server.py              HTTP server (stdlib)
├── rules/
│   └── rule_engine.py         Deterministic rule engine
└── scripts/
    └── smoke_test.py          Pipeline verification
```

---

## Setup

```bash
# No dependencies required. Standard library only.
git clone <repo-url>
cd nexushackathon
```

## Run

```bash
python3 frontend/server.py
# → http://localhost:8080
```

## Verify

```bash
# Smoke test (checks pipeline integrity)
python3 scripts/smoke_test.py

# API contract
curl http://localhost:8080/api/result

# Rule Engine standalone
python3 rules/rule_engine.py
```

---

## Demo Flow (60–90 seconds)

1. Start server → `python3 frontend/server.py`
2. Open browser → `http://localhost:8080`
3. Dashboard loads with "Loading…" → replaced by live data
4. **Operator Dashboard** shows:
   - Scenario ID, Transfer Status (❌ Failed), Risk Level (HIGH 🔴)
   - Risk Score (0.83), Estimated Delay (70 min)
   - Recommendation ("Take the next available KTX")
5. **Passenger View** shows the passenger message
6. Stop the server → reload page → **cached fallback** displays with "cached" badge

---

## Limitations

- **Accuracy is secondary.** The goal is demonstrating integrated mobility data, not production-grade predictions.
- **Mock data.** Current demo uses a single pre-defined scenario. Public API integration is set up but requires an API key to activate.
- **No reservation/payment.** Feature freeze by design — the MVP proves the concept, not the full platform.
- **Single route.** Demo covers one route (Jeju → Gimpo → Seoul → Busan). The rule engine works for any route, but only one scenario is provided.

---

## Future Work

- [ ] Connect to real Korail/airport public APIs
- [ ] Multi-route scenario support
- [ ] Timeline visualization in Dashboard
- [ ] Historical delay data for ML-enhanced prediction
- [ ] Mobile-responsive Passenger View

---

Built for **l내일路(로) 해커톤 2026** by the NEXUS team.
