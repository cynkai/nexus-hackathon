# NEXUS Scenario: 인천에서 부산까지

> 30초 안에 상황을 파악할 수 있습니다.
> 이 문서는 **사실(Facts)** 만 기록합니다. 판단과 추천은 Rule Engine이 수행합니다.

---

## 여행자

**김서울** — 후쿠오카 여행을 마치고 부산으로 귀가 중

---

## 원래 일정

| 시간 | 구간 | 탑승물 | 비고 |
|------|------|--------|------|
| 09:00 → 11:10 | 후쿠오카(FUK) → 인천(ICN) | **KE-123** (국제선) | 예정 도착 11:10 |
| 12:20 → 13:03 | 인천공항 → 서울역 | 공항철도 직통(AREX) | 43분 소요 |
| **13:30 → 16:00** | **서울역 → 부산역** | **KTX-105** | 2시간 30분 |

---

## 지연 이벤트 ✈️

| 항목 | 값 |
|------|----|
| 항공편 | KE-123 (후쿠오카 → 인천) |
| 예정 도착 | 11:10 |
| 실제 도착 | 11:55 |
| 지연 | **+45분** |

---

## 환승 경로 상세

인천공항 1터미널 도착 후 서울역 KTX 승강장까지의 소요시간 구성:

| 항목 | 소요시간(분) | 비고 |
|------|:----------:|------|
| 입국심사 | 40 | 인천공항공사 통계 기준 상한 |
| 수하물 수취 | 15 | 항공사 평균 |
| 공항철도 승강장 이동 | 10 | 터미널 내 |
| 공항철도 직통 (ICN→서울역) | 43 | AREX Express |
| KTX 승강장 이동 | 10 | 서울역 내 |
| **합계** | **118** | |

---

## 환승 불가 🚫

KE-123이 45분 지연되면서 KTX-105(13:30 출발)로의 환승이 불가능합니다.

| 항목 | 값 |
|------|----|
| Arrival (KE-123) | 11:55 |
| Departure (KTX-105) | 13:30 |
| Available Transfer Time | 95 min |
| Required Transfer Time | 118 min |
| Transfer Status | **Impossible** |
| 부족 시간 | **23분** |

---

## Pipeline

```
Input                          Rule Engine                     Output
─────                          ───────────                     ──────
Flight arrival                 risk = calculate(...)           Risk Score
Flight delay                   recommendation = recommend(...) Recommendation
Transfer profile                                             ETA
Rail timetable                                              Local suggestions
```

---

## Expected Output (Dashboard Contract)

Dashboard는 Rule Engine의 결과를 받아 승객에게 다음을 표시합니다.

- Delay notice (지연 안내)
- Recommended route (추천 경로)
- Risk score (위험도)
- Estimated arrival time (예상 도착 시간)
- Local suggestions (도착지 지역 관광/상권 추천)
