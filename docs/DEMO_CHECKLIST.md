# NEXUS Demo Checklist

> Use this checklist before and during your hackathon judging presentation.

---

## Before Demo

### Environment

- [ ] Python 3 installed (`python3 --version`)
- [ ] All files present (`ls nexus-hackathon/`)
- [ ] Smoke test passes (`python3 scripts/smoke_test.py`)
- [ ] Server starts (`python3 frontend/server.py`)
- [ ] Dashboard loads at `http://localhost:8080`
- [ ] API returns data (`curl http://localhost:8080/api/result`)

### Fallback Verification

- [ ] Server running → Dashboard loads with live data
- [ ] Visit `http://localhost:8080/api/result?fault=1` → reload page → "cached" badge appears
- [ ] No network → Dashboard still works (cached)

### Demo Flow

- [ ] Delay notice visible
- [ ] Transfer failure visible
- [ ] Risk score + level visible
- [ ] Recommendation visible
- [ ] Passenger message visible
- [ ] Whole flow completes within 60 seconds

### Backup

- [ ] Screen recording software ready
- [ ] Backup video recorded (in case of live demo failure)
- [ ] README.md and JUDGE.md printed or accessible offline

---

## During Demo

### Opening (15 seconds)

- [ ] Introduce the problem: *"Rail and aviation systems don't talk to each other. When a flight is delayed, passengers don't know if they can still catch their train."*
- [ ] State what NEXUS does: *"We detect the delay, check the transfer, calculate the risk, and tell the passenger what to do."*

### Live Demo (30 seconds)

- [ ] Show Dashboard loading
- [ ] Point to Scenario ID (SC001)
- [ ] Point to **❌ Failed** transfer status
- [ ] Point to **MEDIUM 🟠** risk level + **0.17** score
- [ ] Point to **30 min** estimated delay
- [ ] Point to **"Take KTX-110 at 14:00"** recommendation
- [ ] Point to **Passenger View** message (Korean)
- [ ] Point to **주변 장소 추천** panel (local suggestions)

### Technical Explanation (15 seconds)

- [ ] Explain the pipeline: Facts → Rule Engine → Dashboard
- [ ] Emphasize rules are deterministic (no black box)
- [ ] Show public API architecture: normalization layer is implemented, endpoint is ready to connect

### Closing (10 seconds)

- [ ] Summarize value: *"Integrated mobility data → better transfer decisions → explainable recommendations."*
- [ ] Ask for questions

### Total: ~70 seconds

---

## Q&A Preparation

| Likely question | Suggested answer |
|----------------|-----------------|
| "Is this using real data?" | "Currently mock data. The normalization layer for public API data is implemented and ready; the API endpoint is not yet connected." |
| "How accurate is the risk score?" | "Deterministic rule-based. Accuracy improves as more data sources are connected." |
| "Can this scale to the whole country?" | "The architecture is extensible — add more routes, more data sources, and the same pipeline works." |
| "Why not use AI/ML?" | "For a hackathon MVP, deterministic rules are more reliable for demo. ML enhancement is an optional future layer." |
| "What if the internet goes down?" | "The dashboard caches the last result in the browser (localStorage). Works offline." |

---

## Scoring Criteria Reference

| Criteria | How NEXUS addresses it |
|----------|----------------------|
| Problem clarity | Clear: disconnected rail/aviation transfer decisions |
| Technical execution | Clean pipeline, stdlib only, deterministic rules |
| Demo quality | 60-second flow, cached fallback, loading + error states |
| Innovation | Rail + aviation data integration (not done today) |
| Practicality | Real API integration ready, extensible architecture |
