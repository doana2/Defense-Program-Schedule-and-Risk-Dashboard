# Schedule and risk methods

This demonstration follows schedule-assurance concepts in the GAO Schedule Assessment Guide. It is not an official DCMA implementation or certification. Thresholds are review prompts. See SOURCES.md.

## Calendar and progress

All arithmetic uses business-day offsets from 2026-04-06. Monday-Friday, eight hours per day, no holidays. Finish dates are exclusive: a one-day task starting Monday finishes at Tuesday's opening boundary. Project XML translates that finish to Monday 17:00. Simulation percentiles are rounded upward to a whole workday boundary.

Completed tasks retain actual starts/finishes. In-progress tasks retain actual starts and finish at the status date plus remaining duration. Unstarted work cannot start before the status date. The model does not re-open completed work when a predecessor moves. Imported sequencing is audited before calculation; out-of-sequence actual progress needs human resolution.

## Generalized precedence

NetworkX validates the directed acyclic graph and provides a topological order. Pandas owns tabular inputs, joins, reporting and resource aggregation. For predecessor i, successor j, durations d, starts S and lag L, the forward pass enforces:

| Type | Inequality |
|---|---|
| Finish-to-start | S[j] >= S[i] + d[i] + L |
| Start-to-start | S[j] >= S[i] + L |
| Finish-to-finish | S[j] >= S[i] + d[i] - d[j] + L |
| Start-to-finish | S[j] >= S[i] - d[j] + L |

Lower constraints set earliest permissible dates. Upper constraints enter the backward pass: they can expose negative float, but never force an infeasible forecast earlier. MSO/MFO are represented by lower and upper bounds. The original baseline remains unchanged during a build.

The backward pass applies the reverse inequalities. **Network float** uses the natural calculated program finish without upper date constraints. **Total float** uses the required deadline and task upper constraints. Thus an activity may have zero network float and negative deadline float. Critical means approximately zero network float; near-critical means positive network float up to 10 days. Complete work is excluded from actionable counts. With SS/FF logic a zero-float start is not always duration-driving; the critical-path perturbation test explicitly checks duration propagation.

## Fourteen health screens

Unless specified below, the population is incomplete non-milestone work. Percentages use the numerator and denominator stored alongside each result. Empty populations are N/A. Relationships are counted if their successor is incomplete, including milestone successors.

| # | Indicator | Implementation / review boundary |
|---|---|---|
| 1 | Logic | Missing predecessor or successor; review above 5%. T001 and T152 are allowed endpoints. |
| 2 | Leads | Negative-lag relationships; review any. |
| 3 | Lags | Positive-lag relationships; review above 5%. |
| 4 | Relationship types | FS share of relationships; review below 90%. |
| 5 | Hard constraints | MSO/MFO/SNLT/FNLT; review above 5%. |
| 6 | High float | Total float >44 workdays; review above 5%. |
| 7 | Negative float | Total float <0; review any. |
| 8 | High duration | Current total duration >44 workdays; review above 5%. |
| 9 | Invalid dates | Finish before start, unfinished work finishing before status, unstarted work starting before status, future actuals; review any. |
| 10 | Resources | No assignment record on an incomplete activity; review any. |
| 11 | Missed tasks | Baseline-due detail work either incomplete or completed late / all baseline-due detail work; review above 5%. |
| 12 | Critical-path test | Add 600 workdays to an incomplete zero-network-float activity's remaining duration. Test candidates until one causes exactly 600 days of final delay. Otherwise review. |
| 13 | CPLI proxy | (Remaining program span + final deadline slack) / remaining span; review below 0.95. Span is measured in business days, not a traced duration-sum critical path. |
| 14 | BEI | All completed detail activities / detail activities baseline-due by status; review below 0.95. Early completions can make BEI exceed 1. |

The activity diagnostic report additionally flags unknown references, cycles, self-links, unsupported types, relationship/date sequencing violations, missed milestones, and critical/near-critical work. A final milestone constraint can appear in diagnostics while being outside the non-milestone population for point 5. The seeded 48-day logistics task is complete, so it is outside point 8's current screening population.

The 44-day and 10-day thresholds are code constants; matching config fields document the scenario but do not currently override those constants. The engine's calendar origin is also fixed in engine.py. Change these in code and rerun tests when adapting the model.

## Resource demand

Each assignment is uniform FTE over its remaining active business days. Pool/day demand is the sum of concurrent assignments. Conflict = max(demand - capacity, 0). Overloaded resource-days count pool/day pairs, not distinct calendar days or people. Excess FTE-days sum the daily excess. Neither CPM nor Monte Carlo performs resource leveling.

## Monte Carlo schedule risk assessment

Default: 5,000 trials, NumPy generator seed 27. For each task, sample triangular remaining duration with lower = remaining x low_factor, mode = remaining, upper = remaining x high_factor. Equal bounds produce a constant. Actual progress is fixed.

For each Open risk, sample Bernoulli occurrence using its probability and a triangular conditional delay using its low/mode/high impacts. Add delay only to incomplete mapped tasks. A risk mapped to several tasks shares the same occurrence and impact, creating explicit correlation for those targets. Other duration draws and risk events are independent. Known realized issues are already in the deterministic input and are not resampled.

Every trial reruns the precedence network. Program completion is the maximum task finish. P50/P80 use empirical right-continuous quantiles (`method='higher'`) and dates round up to working-day boundaries. Each milestone also gets P50/P80 and an empirical probability of meeting its own baseline. No trials on time is a 0% sample result, not proof of impossibility.

Risk sensitivity is the difference in average finish between trials where a risk occurred and trials where it did not. It is a descriptive conditional statistic, not a causal attribution or a sum of program delays. Register expected impact = probability x mean(low, mode, high); it is task exposure, not additive program delay.

Uncertainty ranges are fictional. Holidays, resource leveling, cost, split tasks, feedback/rework loops and general duration correlation are absent. P80 is conditional on these assumptions and is not a contractual confidence guarantee.

## Milestones and changes

Complete milestones take precedence in reporting. An incomplete baseline milestone before status is Missed. Otherwise it is At risk when forecast slip >0 or empirical on-baseline probability <80%. Other milestones are On track.

Change requests and approval events are separate CSVs. Only CR-001 is reflected in the current schedule; pending/rejected requests do not change forecast inputs. This is an illustrative audit trail, not an authenticated approval system. Editing approval text alone never mutates the schedule.
