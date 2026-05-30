# AI Review Cockpit — End-to-End Demo Guide

This guide walks through the complete AI Review Cockpit workflow, from submitting a PR to reviewing the cockpit report and GitHub comment.

## Prerequisites

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env: set GITHUB_TOKEN, AI_API_KEY

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start server
python main.py

# 4. Open browser
open http://localhost:8000
```

## Demo Walkthrough

### Step 1: Home Page — Submit a PR

Navigate to `http://localhost:8000`. The home page presents a product landing page with:

```
┌──────────────────────────────────────────────────────────────┐
│  [AI Review Cockpit]                                         │
│                                                              │
│  Evidence-driven PR Review                                   │
│                                                              │
│  ┌──────────────────────────┐  ┌────────────┐               │
│  │ GitHub PR URL            │  │ Risk Level  │ HIGH          │
│  │ [input________________]  │  │ Findings    │ 6             │
│  │                          │  │ Noise Filter│ 67%           │
│  │ ☐ Auto-comment to GitHub │  │ GitHub Ready│ 2             │
│  │ [Start Review]           │  └────────────┘               │
│  └──────────────────────────┘                               │
│                                                              │
│  Pipeline: 18 raw → 9 deduped → 6 visible → 2 comment-ready │
└──────────────────────────────────────────────────────────────┘
```

1. Enter a GitHub PR URL: `https://github.com/owner/repo/pull/123`
2. (Optional) Enable "Auto-comment to GitHub PR" to post findings
3. (Optional) Provide a GitHub Token with `repo` scope
4. Click **Start Review**

### Step 2: Progress Page — Real-time Pipeline Status

After submission, you're redirected to the task progress page. The system runs a 7-stage pipeline:

```
┌──────────────────────────────────────────────────────────────┐
│  PR #123 ─ owner/repo                                        │
│                                                              │
│  [████████░░░░░░░░░░░░░░░░░░░░░░░] 30%                       │
│  Current: AI File Review                                     │
│                                                              │
│  Stages:                                                     │
│  ✓ FETCHING_PR       — PR info + diff fetched                │
│  ✓ BUILDING_CONTEXT  — Related files identified              │
│  ✓ STATIC_SCAN       — 15 rules checked (2 found)            │
│  ✓ AI_PR_SUMMARY     — PR summary generated                  │
│  ⏳ AI_FILE_REVIEW   — Analyzing files...                    │
│  ☐ AI_CROSS_FILE     — Waiting                              │
│  ☐ MERGING_RESULTS   — Waiting                              │
│                                                              │
│  Changed Files (risk-ranked):                                │
│  ┌──────────────────────────────────────┐                    │
│  │ user_service.py     HIGH   +32/-4    │                    │
│  │ ████████░░░░░░░░░░                   │                    │
│  │ README.md           LOW     +8/-0    │                    │
│  │ ██░░░░░░░░░░░░░░░░                   │                    │
│  └──────────────────────────────────────┘                    │
└──────────────────────────────────────────────────────────────┘
```

The page auto-polls every 2 seconds. When complete, click **View Report**.

### Step 3: Cockpit Report — Decision Dashboard

The report page is the core of the Cockpit experience:

```
┌──────────────────────────────────────────────────────────────┐
│  [Metric Cards]                                              │
│  ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │HIGH    │ │Conf: 78% │ │6 findings│ │Fix before merge   │  │
│  │Risk Lv │ │avg across│ │2 critical│ │Review Decision    │  │
│  └────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
├──────────────┬───────────────────────────────────────────────┤
│ File Risk Map│ [Pipeline Bar]                                │
│ ─────────────│ Raw:18 → Deduped:9 → Visible:6 → GH Ready:2  │
│ user_svc.py  │                                               │
│ ████████░ 80%│ [Review Decision Card]                        │
│ +32/-4 3 fnd│ Decision: Fix before merge — 存在 high 风险    │
│ deep review  │ Reasons:                                      │
│              │  • Hardcoded password in user_service.py       │
│ README.md    │  • Unsafe SQL delete in user_dao.py           │
│ ██░░░░░░ 10% │                                               │
│ +8/-0 clean  │ [Findings by Severity]                        │
│ skip         │ ┌─ Critical ──────────────────────────────┐   │
│              │ │ Hardcoded password detected [S005]       │   │
│ [Overview]   │ │ conf: 85% ████████████████░              │   │
│ Critical: 1  │ │ user_service.py:42                       │   │
│ High: 1      │ │ Evidence Chain:                          │   │
│ Medium: 0    │ │ File→S005 hardcoded_password→85% conf    │   │
│ Low: 0       │ │ Suggestion: Use env vars not literals    │   │
│              │ └──────────────────────────────────────────┘   │
│ Key Focus:   │ ┌─ High ──────────────────────────────────┐   │
│ • Hardcoded  │ │ Unsafe delete without WHERE [S014]      │   │
│   password   │ │ conf: 85% ████████████████░              │   │
│              │ │ user_dao.py:88                           │   │
│              │ └──────────────────────────────────────────┘   │
└──────────────┴───────────────────────────────────────────────┘
```

**Key features on this page:**

| Feature | Description |
|---------|-------------|
| **Metric Cards** | Risk Level, Avg Confidence, Finding counts, Merge Decision |
| **File Risk Map** | Click any file to filter findings by file |
| **Pipeline Bar** | Raw → Deduped → Confidence Gate → GitHub Ready |
| **Review Decision** | "Block merge" / "Fix before merge" / "Review recommended" / "Ready to merge" |
| **Severity Tabs** | Filter findings by severity level |
| **Confidence Filter** | Toggle `Hide low conf (< 0.60)` |
| **Evidence Chain** | Each finding shows evidence trace |
| **Feedback Buttons** | Mark findings as Valid / FP / Resolved |
| **Keyboard Shortcuts** | `1-5` filter, `F` next, `R` refresh |

### Step 4: GitHub PR Comment

If `auto_comment` was enabled, the system posts a structured comment to the PR:

```
## 🤖 AI Code Review

**Risk Level:** HIGH
**Merge Suggestion:** 建议修复 high 及以上风险后再合并
**Findings Found:** 3

### Key Focus
- Hardcoded password in user_service.py
- Unsafe delete in user_dao.py

### High Risk Issues
1. `user_service.py:42` — Hardcoded password detected [S005] (conf: 85%)
2. `user_dao.py:88` — Unsafe delete without WHERE [S014] (conf: 85%)

### Evidence Summary
- **Hardcoded password** (`user_service.py`): Hardcoded password/secret detected
- **Unsafe delete** (`user_dao.py`): Delete/update without obvious WHERE condition
```

The comment is *idempotent* — re-running the review updates the existing comment instead of creating a new one.

## What to Try

| Scenario | PR Type | Expected Result |
|----------|---------|----------------|
| Documentation change | Only `.md` files | LOW risk, no findings |
| Business logic change | Service methods without tests | MEDIUM risk, S015 flagged |
| Security issue | Hardcoded passwords, unsafe SQL | HIGH risk, S005/S014 at conf 0.85 |
| Mixed PR | Multiple file types | Varies by file risk levels |
