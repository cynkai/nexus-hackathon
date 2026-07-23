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
- [ ] Server stopped → Page reload → "cached" badge appears
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
- [ ] Point to **HIGH 🔴** risk level + **0.83** score
- [ ] Point to **70 min** estimated delay
- [ ] Point to **"Take the next available KTX"** recommendation
- [ ] Point to **Passenger View** message

### Technical Explanation (15 seconds)

- [ ] Explain the pipeline: Facts → Rule Engine → Dashboard
- [ ] Emphasize rules are deterministic (no black box)
- [ ] Show public API architecture is ready (activate with API key)

### Closing (10 seconds)

- [ ] Summarize value: *"Integrated mobility data → better transfer decisions → explainable recommendations."*
- [ ] Ask for questions

### Total: ~70 seconds

---

## Q&A Preparation

| Likely question | Suggested answer |
|----------------|-----------------|
| "Is this using real data?" | "Currently mock data, but the public API integration is ready. Activate with a data.go.kr API key." |
| "How accurate is the risk score?" | "Deterministic rule-based. Accuracy improves as more data sources are connected." |
| "Can this scale to the whole country?" | "The architecture is extensible — add more routes, more data sources, and the same pipeline works." |
| "Why not use AI/ML?" | "For a hackathon MVP, deterministic rules are more reliable for demo. ML enhancement is an optional future layer." |
| "What if the internet goes down?" | "The dashboard caches the last result in the browser. Works offline." |

---

## Scoring Criteria Reference

| Criteria | How NEXUS addresses it |
|----------|----------------------|
| Problem clarity | Clear: disconnected rail/aviation transfer decisions |
| Technical execution | Clean pipeline, stdlib only, deterministic rules |
| Demo quality | 60-second flow, cached fallback, loading + error states |
| Innovation | Rail + aviation data integration (not done today) |
| Practicality | Real API integration ready, extensible architecture |
