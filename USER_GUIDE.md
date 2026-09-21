# Complete walkthrough

## 1. Program and data ownership

MERIDIAN M-27 is a fictional flight-research demonstrator. The dataset tracks only program-level work, not aircraft design parameters or weapon capabilities.

There are 120 work activities and 32 milestones. Five phases each contain six work packages. Each work package contains four work activities and a gate. Authorization and final acceptance are the remaining two milestones. Project XML also includes 35 summary rows (five phases + thirty work packages), for 187 visible task rows.

Engineering and logistics start together. Software follows early engineering releases. Testing waits for both final engineering and software gates. Delivery waits for testing and logistics readiness. Two parallel work-package branches flow through each phase.

`data/schedule.csv` owns task inputs. `dependencies.csv` owns logic. Assignments join task IDs to resource IDs. Risks join to one or more task IDs separated by semicolons. Change requests and approval events join on change ID.

The original baseline is immutable during `build`. The generator creates it before adding the current forecast changes. CR-001 adds 24 workdays to T058's activity duration, but overlap/float absorb six days: the final acceptance slips 18 days. A separate realized logistics-duration issue changes T068 to 48 days. Those known changes are already in current durations and are not sampled again as discrete risks.

## 2. Data dictionary

### Schedule

| Field | Meaning |
|---|---|
| `id` | Stable unique task ID, e.g. T058 |
| `wbs` | Phase.work-package.activity code |
| `name`, `phase`, `work_package` | Human-readable scope |
| `duration` | Current total planned working-day duration; zero = milestone |
| `remaining` | Working-day duration still to execute at the status date |
| `percent_complete` | 0-100 progress indicator; not an earned-value metric |
| `actual_start`, `actual_finish` | Actual date boundaries; blank when unavailable |
| `baseline_start`, `baseline_finish` | Original approved snapshot |
| `current_start`, `current_finish` | Imported forecast dates audited before CPM recalculation |
| `constraint` | ASAP, SNET, FNET, SNLT, FNLT, MSO or MFO |
| `constraint_date` | Required for a non-ASAP constraint |
| `low_factor`, `high_factor` | Three-point remaining-duration bounds around the most likely remaining duration |

Completed work requires both actual dates and zero remaining duration. In-progress work requires an actual start and no actual finish. Remaining work cannot be forecast before the status date. Dates must be valid working days for actuals and constraint inputs. Use zero duration/remaining and 100% complete for an achieved milestone.

### Dependencies

`pred,succ,type,lag`: task IDs, FS/SS/FF/SF, and signed working-day lag. Positive lag waits; negative lag is a lead and receives a diagnostic. Do not add summary-task links. Unknown IDs, self-dependencies, duplicate links and cycles are invalid.

### Resources and risks

`resources.csv` gives pool ID, name and capacity in FTE. `assignments.csv` gives task ID, pool ID and assignment units. One unit means one full-time person during each active workday, not one percent. Demand greater than capacity creates a conflict row.

Risk `probability` is 0-1. `impact_low`, `impact_mode`, `impact_high` are additional working-day duration impacts conditional on occurrence. Each risk includes an owner, mitigation and status. Only Open risks affect simulation, and completed target tasks never receive sampled delay. RISK-05 remains in the sample register although its engineering target is complete: it is retained as a register-closure housekeeping example and contributes no simulated delay. The register's gross expected exposure is not a sum of future program delay.

## 3. Run and inspect

Install with the README commands, then run `meridian build`. The CLI first audits the imported dates and relationships. It refuses to produce a forecast when dates or sequencing are invalid or the graph has invalid references/cycles. It writes the import diagnostic CSV before stopping.

The normal build performs these steps:

1. Read the eight input datasets and configuration.
2. Validate the graph and task fields, then audit imported dates.
3. Run a forward pass for feasible start/finish dates.
4. Run backward passes for network float and deadline/constraint float.
5. Aggregate assignments into daily pool demand and conflicts.
6. Calculate the 14-point health indicators and activity-level findings.
7. Sample remaining durations and discrete risks across seeded trials.
8. Recalculate the network in every trial and extract completion percentiles.
9. Export current results, native-app interchange and reports.

`outputs/schedule_analysis.csv` contains early days, late days, baseline variance, network float, total float and path status. Completed tasks retain actual dates. Their float is historical rather than actionable; dashboard counts exclude them from critical/negative remaining work.

## 4. Explore the offline dashboard

Open `outputs/dashboard.html` locally in Chrome, Edge or Firefox. All data and JavaScript are embedded. There are no CDN requests or account connections.

| Tab | What to inspect |
|---|---|
| Overview | Acceptance forecast, P80 date, at-risk milestones, phase bars and assurance counts |
| Schedule | Search IDs/names, filter phases and path status, inspect dependency strings and both float measures |
| Risks | Probability/impact register, P50/P80 and gross expected task impacts |
| Resources | Capacity vs peak demand and every overloaded pool/day with concurrent task IDs |
| Health | All 14 indicators, thresholds, numerators, denominators and detailed findings |
| Changes | Requests, application status and approval events |

Filters only change the view; they do not alter inputs or run a new forecast. The change view is read-only.

## 5. Microsoft Project Desktop

1. Keep a copy of the committed XML.
2. In licensed Project Desktop choose File > Open, browse to `project/meridian.xml`, and open it as a new project.
3. Use the included Monday-Friday calendar. Check eight-hour days and the September 18, 2026 status date.
4. Expand the WBS. Confirm 152 leaf records plus 35 summary rows, six resource pools and 180 assignments.
5. Add Baseline Start, Baseline Finish, Start, Finish, Total Slack, Constraint Type and Resource Names columns.
6. Inspect predecessor types: FS=1, SS=3 and FF=0 in the XML. One working day of link lag equals 4,800 tenths of a minute.
7. Compare leaf dates before and after Project recalculates. Python uses an exclusive next-workday 08:00 finish boundary. XML translates nonzero-duration finishes to the preceding working day at 17:00; zero-duration milestones remain at 08:00. Thus dates can differ by one business day in their displayed finish field without a duration difference.
8. Review resource overallocations and, in a separate scenario, try resource leveling. Do not describe the Python forecast as leveled.
9. Save as `.mpp` only after the desktop check succeeds. Capture your own Project screenshots for stronger evidence of hands-on use.

Native Project parsing/recalculation was not performed in the build environment. Fixed constraints, status updates and mixed relationships may calculate differently in a commercial engine. The CSV/Python model remains the reference until you reconcile these differences.

## 6. Tableau Desktop

Open `bi/meridian.twbx`. It packages the `.twb` and five small CSV data sources. The workbook defines a four-sheet Program Review dashboard plus a completion-trials-by-week worksheet.

| Sheet | Category | Measure |
|---|---|---|
| Phase finish slip | Phase | Maximum task finish variance within phase |
| Expected risk impact | Risk title | Probability x mean conditional task impact |
| Peak demand to capacity | Resource ID | Maximum daily demand/capacity |
| Milestone slip by WBS | WBS | Current minus baseline finish in business days |
| Completion trials by week | Completion week | Trial count |

The native Tableau files are generated XML candidates. They have not been opened/rendered in Tableau. If a source path needs repair, unpack `.twbx` as ZIP, open `.twb`, and reconnect each `dataN` source to the matching `Data/dataN.csv`. If worksheet compatibility fails, rebuild each sheet: Label on Rows, SUM(Value) on Columns, Bar mark; assemble the first four on a 1600x1000 dashboard. Use the exact labels in the table above. Do not label the phase maximum task variance as phase-gate delay.

For richer Tableau exploration, connect directly to `outputs/schedule_analysis.csv`, `milestones.csv`, `risks.csv` and `resource_load.csv` as separate sources. Build a Gantt with task name on Rows, Current Start on Columns (exact date), duration/finish span on Size, and Path Status on Color. Use calendar-day span for a continuous date axis; Python duration is in business days. Add Phase and Path Status filters.

All included data are fictional and suitable for a public portfolio. Tableau Public is optional, not necessary; publishing any future real dataset requires its owner's permission.

## 7. Excel reporting

The workbook has Overview, Milestones, Risks, Changes, History and Health tabs. Probability inputs, dates and numeric values use real cell types. Expected risk impact, business-day milestone variance, milestone status and overview totals use formulas. The workbook includes filters, frozen headers and conditional formatting.

You may edit the risk probability and impacts to explore expected task exposure in Excel. P50/P80 and CPM results remain **snapshots**. Export/update the canonical risk CSV and run Python to refresh those results. A change to probability in Excel alone cannot change the simulated P80 date.

After a Python rebuild, replace source values in the corresponding Excel table using the output CSV, matched by ID, retaining formula columns. Update status/forecast/SRA scalar snapshots on Overview. Do not paste text over formulas. Keep a copy before updating. The included Office files are editable snapshots; their original authoring runtime is not a dependency of this repository.

## 8. Change control and refresh

The three seeded requests show the lifecycle; this is not an approval service. An Approved text value does not execute a mutation. To apply a new approved change:

1. Record the request, before/after field values, rationale, owner and date in changes.csv.
2. Append a new decision event in change_history.csv. Do not erase prior events.
3. Apply the approved values to the relevant schedule/remaining-duration input. Update current imported dates consistently, or first compute a draft with `solve` and inspect it.
4. Leave the baseline columns unchanged unless a separate rebaseline decision authorizes a new version.
5. Run the audit and build, compare milestone deltas and document the impact.
6. Refresh Tableau, Excel and PMR presentation snapshots, then commit the changes together.

There is no authentication, electronic signature, immutable datastore or concurrency control. Use Git history as the portfolio's version record, not as an enterprise approval system.

## 9. Regeneration boundaries

| Artifact | Regeneration |
|---|---|
| Data fixtures | `meridian generate`; overwrites selected fixture directory |
| CSV/JSON/HTML/PNG charts/PDF/Project XML/Tableau | `meridian build` |
| XLSX/PPTX | Included editable snapshots; manually refresh from CSV/JSON results. Office authoring is not part of the Python build. |
| Dashboard screenshots | `node scripts/preview.mjs /path/to/repo` after installing Playwright and its Chromium browser in your local Node environment |

The core analysis is portable open-source Python. Update the editable Office files manually from the refreshed CSV/JSON outputs; these files are not part of the automated CI regeneration pipeline.

## 10. What to explain in an interview

Explain why a 24-day activity change causes an 18-day program delay. Contrast zero network float with negative deadline float. Demonstrate the flawed submission and show why the build refuses it. Change one risk probability in a copied scenario and compare Monte Carlo percentiles. Show a resource conflict and explain why a resource-unconstrained forecast can still be optimistic.

Describe the project as an AI-assisted fictional portfolio study. Only claim Microsoft Project/Tableau hands-on validation after you actually perform the desktop steps. A useful next improvement is a separately tested resource-leveling algorithm followed by a before/after recovery analysis.
