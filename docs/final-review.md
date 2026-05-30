# AI Review Cockpit — Final Project Review

## 1. Project Overview

AI Review Cockpit is a low-noise, explainable, decision-oriented AI code review system for GitHub Pull Requests.

It is not a simple "diff to LLM" tool. Instead, it:

1. Parses changed lines from the unified diff (ignoring unchanged code)
2. Scores each file by risk to determine analysis depth
3. Runs 15 static rules on new code only
4. Performs AI file-level and cross-file analysis
5. Merges findings with signature-based dedup
6. Calculates confidence scores with agreement bonuses
7. Generates a **Review Decision Cockpit** report
8. Optionally posts high-confidence findings to the GitHub PR conversation

**Target users:** PR authors, reviewers, and team leads who need to make fast, informed merge decisions.

---

## 2. Complete Workflow

```
┌──────────────────────────────────────────────────────────────┐
│  Input                                                        │
│  GitHub PR URL → GitHubClient fetches diff + file list        │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│  Stage 1: FETCHING_PR                                        │
│  Parse URL, fetch PR metadata, changed files, patches         │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│  Stage 2: BUILDING_CONTEXT                                   │
│  Identify related files (controller→service→mapper)          │
│  Fetch context for deep-analysis files                        │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│  Stage 3: STATIC_SCAN                                        │
│  15 rules on added lines only (S001-S015)                    │
│  No flagging of pre-existing issues                          │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│  Stage 4: AI_PR_SUMMARY                                      │
│  LLM generates one-line summary, module changes,              │
│  business impact                                              │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│  Stage 5: AI_FILE_REVIEW                                     │
│  Files sorted by risk score (highest first).                  │
│  High-risk → deep review (full content + related context)     │
│  Normal-risk → patch-only review                              │
│  Low-risk → skip                                               │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│  Stage 6: AI_CROSS_FILE                                      │
│  Cross-file consistency analysis (requires ≥2 changed files)  │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│  Stage 7: MERGING_RESULTS                                     │
│  Signature dedup (file + type + line bucket + title)          │
│  Confidence calculation with agreement bonus                  │
│  Threshold filtering: ≥0.60 visible, ≥0.80 GitHub-ready       │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│  Output                                                       │
│  Cockpit Report (web) + optional GitHub PR comment            │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Core Innovations

### Changed-Line Review

Traditional AI review tools scan the full file and flag pre-existing issues as if they were new. AI Review Cockpit only analyzes **added and modified lines** from the unified diff patch.

```python
# diff_utils.py: parse_patch() extracts only added lines
added_lines = [line for line in hunk_lines if line.startswith('+')]
```

**Result:** Zero noise from legacy code. Every finding is relevant to the current PR.

### Risk-Aware Routing

Files are scored by three factors:
- **Path patterns**: controller/service files score higher, test/docs score lower
- **Change size**: large additions increase risk
- **Content keywords**: database operations, security-sensitive APIs increase risk

Score range: `-2` to `15`. Thresholds determine analysis depth:
- `>= 8`: deep review (full content + related file context)
- `>= 4`: normal review (patch only + summary)
- `< 4`: skip (no AI analysis needed)

**Result:** AI compute is focused on files that matter. Low-risk files (README, config) don't waste LLM context.

### Hybrid Rule + AI

| Category | Rules | AI |
|----------|-------|----|
| Security | S005 hardcoded passwords, S014 unsafe SQL | S006 missing null check |
| Reliability | S003 empty catch, S010 broad exception | S013 transaction risk |
| Performance | S011 loop DB call | S012 missing pagination |
| Quality | S001 debug print, S002 TODO/FIXME | S007 large method |
| Coverage | S008 missing auth, S009 missing validation | S015 test gap |

**When both rule and AI flag the same issue, confidence gets a +0.20 agreement bonus.**

### Confidence Gate

Every finding has a confidence score calculated by:

```
confidence = base_score (by source) + evidence_score + agreement_bonus - uncertainty_penalty
```

Thresholds:
| Score | Visibility | GitHub Comment |
|-------|-----------|----------------|
| ≥ 0.80 | Report + GitHub | Posted automatically |
| 0.60–0.79 | Report only | Not posted |
| < 0.60 | Hidden by default | Never posted |

**Result:** Low-quality findings are suppressed by default. Only actionable findings reach reviewers.

### Evidence Chain

Each finding carries a structured evidence trace:

```
user_service.py:42 → S005 hardcoded_password → 85% confidence (GitHub-ready)
```

Stored as JSON in the database, displayed in the report UI, and included in GitHub PR comments.

**Result:** Reviewers can see exactly why each finding was flagged, not just "AI says so."

### Review Decision Cockpit

The report page is designed as a **merge decision aid**, not just a finding list:

- **Metric Cards**: Risk Level, Review Confidence, Finding Counts, Merge Decision
- **Pipeline Bar**: Raw → Deduped → Visible → GitHub-Ready (counts from real pipeline data)
- **File Risk Map**: Visual risk scores with click-to-filter
- **Review Decision Card**: "Block merge" / "Fix before merge" / "Review recommended" / "Ready to merge"
- **Evidence Chain**: Per-finding evidence trace
- **Feedback System**: Valid / False Positive / Resolved
- **Keyboard Shortcuts**: 1–5 filter, F next, R refresh

**Result:** The reviewer knows at a glance whether to merge, what to fix, and where to look first.

---

## 4. Demo Scenarios

| Scenario | Input | Expected Outcome |
|----------|-------|-----------------|
| Low Risk | README.md change only | `LOW` risk, no findings, "Ready to merge" |
| Medium Risk | Service logic change without tests | `MEDIUM` risk, S015 flagged |
| High Risk | Hardcoded passwords + unsafe SQL + N+1 loops | `HIGH` risk, S005/S014 visible at conf 0.85 |

---

## 5. Engineering Quality

- **Framework**: FastAPI + SQLAlchemy + Jinja2 + Bootstrap 5
- **Static Rules**: 15 rules (S001–S015), patch-only scanning
- **Tests**: 28 unit tests across 5 test suites
- **CI**: GitHub Actions (Python 3.10, lint, test, import check)
- **Data**: SQLite with 4 models (Task, ChangedFile, Finding, Feedback)
- **Process**: 13+ PRs with staged delivery (feat, fix, docs, test, ci, prototype)

### Future Direction: shadcn/ui Prototype

An independent React + Tailwind + shadcn/ui prototype exists at `frontend-prototype/`, demonstrating the planned frontend modernization path with the same cockpit layout, evidence chain, and interactive filtering.

---

## 6. Summary

AI Review Cockpit transforms AI code review from "a list of suggestions" to **a merge decision cockpit** by:

1. **Reducing noise** — changed-line only, confidence-gated
2. **Adding explainability** — evidence chain for every finding
3. **Supporting decisions** — cockpit report with clear merge recommendations
4. **Integrating natively** — GitHub PR comments with idempotent updates
5. **Remaining extensible** — shadcn/ui prototype for future frontend migration
