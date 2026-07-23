# NEXUS Scenario: 제주에서 부산까지

> 30초 안에 상황을 파악할 수 있습니다.
> 이 문서는 **사실(Facts)** 만 기록합니다. 판단과 추천은 Rule Engine이 수행합니다.

---

## 여행자

**김서울** — 제주도 여행을 마치고 부산으로 이동 중

---

## 원래 일정

| 시간 | 구간 | 탑승물 |
|------|------|--------|
| 10:00 → 11:10 | 제주 → 김포 | **KE-A** (항공) |
| 11:10 → 11:40 | 김포공항 → 서울역 | 공항철도 |
| **12:00 → 13:30** | **서울역 → 부산역** | **KTX-A** |

---

## 지연 이벤트 ✈️

| 항목 | 값 |
|------|----|
| 항공편 | KE-A (제주 → 김포) |
| 예정 도착 | 11:10 |
| 실제 도착 | 11:55 |
| 지연 | **+45분** |

---

## 환승 불가 🚫

KE-A가 45분 지연되면서 KTX-A(12:00 출발)로의 환승이 불가능합니다.

| 항목 | 값 |
|------|----|
| Arrival (KE-A) | 11:55 |
| Departure (KTX-A) | 12:00 |
| Available Transfer Time | 5 min |
| Required Transfer Time | 30 min |
| Transfer Status | **Impossible** |
| Transfer Feasible | **false** |

---

## Pipeline

```
Input                          Rule Engine                     Output
─────                          ───────────                     ──────
Flight arrival                 risk = calculate(...)           Risk Score
Flight delay                   recommendation = recommend(...) Recommendation
Transfer time                                              ETA
Required transfer time
```

---

## Expected Output (Dashboard Contract)

Dashboard는 Rule Engine의 결과를 받아 승객에게 다음을 표시합니다.

- Delay notice (지연 안내)
- Recommended route (추천 경로)
- Risk score (위험도)
- Estimated arrival time (예상 도착 시간)

---

## Facts Extracted

Task 3(Rule Engine)이 사용할 구조화된 입력 데이터입니다.

```yaml
flight:
  id: KE-A
  origin: Jeju
  destination: Gimpo
  scheduled_arrival: "11:10"
  actual_arrival: "11:55"
  delay_minutes: 45

transfer:
  from: Gimpo
  to: Seoul Station
  available_minutes: 5
  required_minutes: 30
  status: impossible

rail:
  id: KTX-A
  origin: Seoul Station
  destination: Busan
  scheduled_departure: "12:00"
  scheduled_arrival: "13:30"

route:
  origin: Jeju
  destination: Busan
  passenger: 김서울
```
