# NEXUS — Rail + Aviation Transfer Predictor

[![CI](https://github.com/cynkai/nexus-hackathon/actions/workflows/ci.yml/badge.svg)](https://github.com/cynkai/nexus-hackathon/actions/workflows/ci.yml)
![Python stdlib only](https://img.shields.io/badge/dependencies-stdlib_only-brightgreen)

> 내일路(로) 해커톤 2026 출품작에서 출발해 버전을 올려 가는 프로젝트 · [CHANGELOG](CHANGELOG.md) · [Releases](https://github.com/cynkai/nexus-hackathon/releases)

**한국어 요약.** 항공편이 지연됐을 때, 이어서 타려던 KTX 환승이 아직 가능한지 규칙 엔진이 계산하고 위험도·대체 열차·남는 시간 동안의 지역 관광을 추천한다. 판단은 전부 결정적 규칙이고, LLM은 (키를 넣었을 때) 승객 안내 문장만 쓴다. Python 표준 라이브러리만 쓴다.

**NEXUS** demonstrates why combining railway and aviation data enables better transfer decisions than treating each system independently.

---

## Problem

Railway and aviation systems optimize independently. Transfer decisions across both systems remain disconnected. When a flight is delayed, a passenger has no way to know whether their scheduled train transfer is still feasible — and if not, what to do next.

## Solution

NEXUS integrates rail and aviation schedule data to predict transfer disruptions:

1. **Detect** delay events from flight data
2. **Calculate** transfer feasibility using deterministic rules
3. **Score** the travel risk
4. **Generate** explainable recommendations
5. **Suggest** local tourism options near the destination
6. **Display** results via Operator Dashboard + Passenger View

---

## Architecture

```
data/Scenario.json  ─┐
                      ├──→ backend/public_api.py ─→ rules/rule_engine.py ─→ frontend/server.py ─→ frontend/index.html
Public API (future) ─┘         │                        │                       │
                           normalizer              deterministic rules      Dashboard UI
                           (optional)              (judgment layer)        (presentation only)
                                                    │
                                                    ↓
                                              rules/explainer.py
                                              (LLM or template — explanation only)
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
| Judgment deterministic, explanation only LLM | All scores/reason codes are rule-based; LLM generates only the passenger message. Smoke test proves identity (LLM on/off → decision fields are byte-identical) |
| Facts vs. judgment separated | Scenario is facts only; Rule Engine judges; Dashboard presents |
| Public API is optional | Demo always works; API integration is additive |
| No framework in frontend | Stdlib only, zero dependencies, single file |
| Output contract frozen | Dashboard never needs changes when data source changes |

---

## Repository Structure

```
nexus-hackathon/
├── VERSION                    Current version (shown in the dashboard footer)
├── CHANGELOG.md               Release notes
├── AGENTS.md                  AI agent behavior rules
├── PROJECT_CHARTER.md         Project mission and constraints
├── TASKS.md                   Task breakdown
├── README.md                  ← You are here
├── JUDGE.md                   Judges' one-pager
├── backend/
│   ├── __init__.py
│   └── public_api.py          Optional public data source + normalizer
├── data/
│   ├── Scenario.json              Mock schedule data (single source of truth)
│   ├── local_places.json          Busan local tourism places
│   └── transfer_profile.json      Component transfer times (ICN→Seoul Station)
├── docs/
│   ├── DEMO_CHECKLIST.md          Demo preparation checklist
│   └── Scenario.md                Human-readable scenario definition
├── frontend/
│   ├── index.html                 Dashboard + Passenger View UI
│   └── server.py                  HTTP server (stdlib)
├── rules/
│   ├── rule_engine.py             Deterministic rule engine (judgment)
│   ├── explainer.py               LLM or template explanation layer
│   └── local_recommender.py       Rule-based local tourism suggestions
└── scripts/
    └── smoke_test.py              Pipeline verification
```

---

## Setup

```bash
# No dependencies required. Standard library only (Python 3.10+).
git clone https://github.com/cynkai/nexus-hackathon.git
cd nexus-hackathon
```

## Run

```bash
python3 frontend/server.py
# → http://localhost:8080
```

| Environment variable | Default | Meaning |
|---|---|---|
| `PORT` | `8080` | |
| `NEXUS_HOST` | `127.0.0.1` | `0.0.0.0` to open it to your network. With an LLM key set, anyone who can reach it spends your key. |
| `NEXUS_LLM_API_KEY` | (none) | Your own OpenAI key. Without it, passenger messages come from templates. |
| `NEXUS_LLM_MODEL` | `gpt-5.4-mini` | Model that rephrases the template message. |
| `NEXUS_API_KEY` | (none) | Public flight-data API key for `backend/public_api.py` (rail side not implemented). |

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

## Demo Flow (~60 seconds)

1. Start server → `python3 frontend/server.py`
2. Open browser → `http://localhost:8080`
3. Dashboard loads — press 🟢🟠🔴 header buttons to switch:

   | Button | URL | scenario_id | Risk |
   |--------|-----|-------------|------|
   | 🟢 정상 | `?scenario=feasible` | SC000 | LOW / 0.0 / TRANSFER_FEASIBLE |
   | 🟠 지연 | (기본) | SC001 | MEDIUM / 0.17 / TRANSFER_TIME_INSUFFICIENT |
   | 🔴 막차 | `?scenario=lasttrain` | SC002 | CRITICAL / 1.0 / LAST_TRAIN_MISSED |

   → Same rule engine, three different outputs.

4. **Fault fallback** (별도 시연): `?fault=1` → reload → cached badge appears.
   → API 장애 시에도 브라우저 캐시로 마지막 결과 표시.

---

## Limitations

- **Accuracy is secondary.** The goal is demonstrating integrated mobility data, not production-grade predictions.
- **Mock data.** Current demo uses three pre-defined scenarios (feasible/delayed/lasttrain). The flight data normalization layer is implemented (parses public API → scenario format); rail timetable integration is **not yet implemented** — the normalizer outputs an empty timetable, which causes the rule engine to fall back to default behavior. Production connection requires rail timetable API integration.
- **No reservation/payment.** Feature freeze by design — the MVP proves the concept, not the full platform.
- **Single route.** Demo covers one route (Fukuoka → Incheon → Seoul → Busan). The rule engine works for any route, but currently three variations of one route are provided.
- **The LLM only rephrases.** Since v1.1.0 the LLM gets the template message (not the raw data) and may only reword it. `check_message` rejects a rewrite that flips possible/impossible, drops the urgency, the recommended train or the customer-service number, or contains a number the template doesn't — then the template is shown instead. It can't catch every change of meaning (a reworded sentence can still shift nuance), which is why the template stays the reference.

---

## Future Work

- [ ] Connect to real Korail/airport public APIs
- [ ] Multi-route scenario support
- [ ] Timeline visualization in Dashboard
- [ ] Historical delay data for ML-enhanced prediction
- [ ] Mobile-responsive Passenger View

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

Started at **내일路(로) 해커톤 2026** — the submission is kept at the [`hackathon-submission`](https://github.com/cynkai/nexus-hackathon/tree/hackathon-submission) tag. By [cynkai](https://github.com/cynkai).
