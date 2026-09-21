# MERIDIAN M-27: Defense Program Schedule & Risk Dashboard

A fictional, unclassified aircraft-development program that demonstrates integrated scheduling, schedule assurance, resource analysis and quantitative schedule risk analysis.

**152 leaf activities/milestones · 224 dependencies · 30 work packages · 5 phases · 6 resource pools · 5,000 simulation trials**

No real aircraft, government contract, operational information, controlled technical data or employer affiliation is represented. This is an AI-assisted portfolio demonstration, not evidence of professional program experience or a security clearance.

![Offline dashboard overview](outputs/dashboard_overview.png)

## Start here

- Open [the offline dashboard](outputs/dashboard.html) after downloading the repository. No server, account or API key is needed. GitHub's file viewer does not execute HTML.
- Read the [two-page executive report](outputs/executive_report.pdf).
- Open the [seven-slide PMR deck](outputs/program_management_review.pptx).
- Review the [Excel risk and milestone report](outputs/risk_milestone_report.xlsx).
- Import [the Microsoft Project XML](project/meridian.xml) in Project Desktop.
- Open [the packaged Tableau workbook](bi/meridian.twbx) in Tableau Desktop. See the desktop validation caveat below.
- Follow the [full user guide](docs/USER_GUIDE.md) and [methodology](docs/METHODOLOGY.md).
- Review the [validation record and remaining desktop checks](docs/VALIDATION.md).

## What this demonstrates

| Requirement | Implementation |
|---|---|
| Work breakdown structure | Five phases, six work packages per phase, four work activities and one gate per package, plus program start/end |
| Engineering, software, logistics, testing, delivery | Named activities, overlapping branches and cross-phase acceptance logic |
| FS, SS and FF relationships | 224 typed dependency records; engine also supports SF |
| Baseline/current dates | Frozen original baseline and status-date forecast |
| Resource loading | 180 assignments across six FTE-based pools, daily capacity conflicts |
| Critical path and float | Forward/backward passes, network float, deadline float, late dates and path classification |
| Milestones at risk | Baseline slip, missed date and simulated probability flags |
| Risk register | Ten risks with owners, mitigation, probability and three-point conditional delay |
| Change control | Approved, pending and rejected requests with a separate event history |
| CSV diagnostics | Unknown/missing logic, cycles, dates, sequencing, excessive durations, hard constraints, float and milestone exceptions |
| Schedule health | All 14 named DCMA-style indicators with explicit populations and thresholds |
| Monte Carlo SRA | 5,000 seeded trials, P50/P80 dates, empirical on-time probability and risk sensitivity |
| Portfolio reports | Browser screenshots, Excel workbook, two-page PDF and editable PowerPoint deck |

## Reproduce the Python analysis

Python 3.10 or newer. These commands do not use commercial software or paid cloud services.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux instead:
# source .venv/bin/activate

python -m pip install -e .
python -m unittest discover -s tests -v
meridian build --trials 5000 --seed 27
```

`meridian build` reads the committed inputs. It refreshes CSV results, JSON, the offline HTML dashboard, chart PNGs, the executive PDF, Project XML and Tableau files. It does **not** regenerate the committed XLSX, PPTX or browser screenshots. Their separate build/refresh paths are documented in the user guide.

To recreate the fictional inputs from scratch:

```bash
meridian generate --data data
```

**Warning:** `generate` overwrites the fictional input CSVs in the selected directory. Use a new directory to preserve your edits. `build` overwrites generated results in `--out`; use a separate output directory for comparisons. Do not rerun `generate` during ordinary schedule updates.

Demonstrate a rejected supplier submission:

```bash
meridian audit data/qa_bad_schedule.csv data/qa_bad_dependencies.csv --out outputs/vendor_audit.csv
```

An exit code of **1 is expected** for this intentionally flawed fixture. Unknown references, a self-loop/cycle, missing logic, a lead and stale forecast dates appear in the audit output. The main forecast refuses invalid dates/sequencing or structurally broken logic.

## Included results

The committed snapshot uses status **2026-09-18** and seed **27**. Authoritative values live in [summary.json](outputs/summary.json).

| Metric | Included snapshot |
|---|---|
| Original acceptance baseline | 2027-08-26 |
| Current acceptance forecast | 2027-09-21 |
| Baseline slip | 18 business days |
| P50 completion | 2027-10-08 |
| P80 completion | 2027-10-14 |
| Complete items | 78 of 152 |
| At-risk/missed milestones | 16 |
| Overloaded resource-days | 162 |

These are fictional model outputs, not industry benchmarks. A 0% empirical on-time result means no sampled trial met the deadline; it does not establish a mathematically impossible outcome.

## Repository map

| Path | Purpose |
|---|---|
| `src/meridian/engine.py` | Calendar, validation, generalized CPM, daily resource demand |
| `src/meridian/analysis.py` | Diagnostics, 14-point screening, Monte Carlo |
| `src/meridian/demo.py` | Reproducible fictional program generator |
| `src/meridian/cli.py` | Command-line workflow and reporting pipeline |
| `src/meridian/exports.py` | Project/Tableau exports, charts and executive report |
| `src/meridian/dashboard_template.html` | Self-contained offline dashboard |
| `data/` | Authoritative task, dependency, resource, risk and change records |
| `outputs/` | Committed analysis and portfolio deliverables |
| `project/` | Microsoft Project XML interchange file |
| `bi/` | Native Tableau workbook and packaged CSV data |
| `tests/` | Automated regression tests |
| `scripts/` | Browser screenshot and interaction-check script |
| `.github/workflows/test.yml` | GitHub Actions test and demo-build workflow |

## Important limits

- **Not an `.mpp` file.** Microsoft Project XML is the interchange handoff. Open it, inspect/recalculate it and save as `.mpp` in licensed Project Desktop. The desktop import has not been executed here.
- **Tableau desktop check outstanding.** The `.twb`/`.twbx` contains editable worksheet definitions and local CSV data, but has not been opened or rendered in Tableau. Compatibility may require reconnecting data or rebuilding sheets using the supplied recipe. Included dashboard screenshots come from the offline HTML companion, not Tableau.
- **No automatic resource leveling.** Conflicts are measured, not translated into resource-feasible dates. The deterministic/SRA dates are precedence-network forecasts.
- **Not official DCMA compliance.** This is a documented 14-point-inspired screening implementation. CPLI is a simplified remaining-span proxy. Thresholds are review prompts.
- One Monday-Friday calendar, eight hours/day, no holidays, no split tasks, no time-of-day planning. CSV finish dates are exclusive workday boundaries.
- Baseline changes and approvals are recorded data, not an authenticated multi-user workflow. Changing a request's status alone does not apply it.
- Office presentation files are snapshots. Excel exposure/variance/status formulas recalculate locally, but editing Excel does not rerun the Python network or Monte Carlo model.

## Publish to your GitHub

Create a repository, extract this project folder, and commit its contents. No tokens or personal résumé data are included.

```bash
git init
git add .
git commit -m "Add fictional aircraft schedule assurance portfolio"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/meridian-schedule.git
git push -u origin main
```

Run those commands only inside the extracted project folder. For an existing repository, use its existing remote and branch rather than replacing them. Consider uploading the ZIP as a release asset and pinning the repository on your profile.

## Sources

Method references and exact source links appear in [SOURCES.md](docs/SOURCES.md). This implementation uses the GAO schedule guide as conceptual grounding and Microsoft's published XML field definitions for interchange.
