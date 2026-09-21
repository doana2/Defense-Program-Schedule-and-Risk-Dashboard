"""Day-resolution generalized precedence CPM. All dates are business-day boundaries.

Finish is exclusive: Monday + one workday = Tuesday 08:00. No holidays.
Completed and started work retain actual starts. Remaining work cannot occur
before the status date. Deadline/upper constraints report infeasibility instead
of pulling an impossible forecast earlier. Resource leveling is NOT performed.
"""
import math
import numpy as np
import pandas as pd
import networkx as nx

START = "2026-04-06"
STATUS = "2026-09-18"
VALID_LINKS = {"FS", "SS", "FF", "SF"}
VALID_CONSTRAINTS = {"ASAP", "SNET", "FNET", "SNLT", "FNLT", "MSO", "MFO"}

def day(date, origin=START):
    return int(np.busday_count(origin, str(date)[:10]))

def date_at(offset, origin=START):
    return str(np.busday_offset(origin, int(math.ceil(offset)), roll="forward"))

def validate(tasks, links):
    required = {"id", "name", "duration", "remaining", "percent_complete", "actual_start", "actual_finish", "constraint", "constraint_date"}
    if required - set(tasks):
        raise ValueError(f"Missing task columns: {sorted(required-set(tasks))}")
    if tasks.id.duplicated().any():
        raise ValueError("Duplicate task IDs")
    if not {"pred", "succ", "type", "lag"}.issubset(links):
        raise ValueError("Dependencies need pred,succ,type,lag")
    ids = set(tasks.id)
    if (set(links.pred) | set(links.succ)) - ids:
        raise ValueError("Dependency references unknown task IDs")
    if not set(links.type).issubset(VALID_LINKS):
        raise ValueError("Unsupported relationship type")
    if not set(tasks.constraint).issubset(VALID_CONSTRAINTS):
        raise ValueError("Unsupported constraint type")
    if (links.pred == links.succ).any():
        raise ValueError("Self dependency")
    if links.duplicated(["pred", "succ", "type"]).any():
        raise ValueError("Duplicate dependency")
    for col in ["duration", "remaining", "percent_complete"]:
        a = pd.to_numeric(tasks[col], errors="coerce")
        if a.isna().any() or (~np.isfinite(a)).any() or (a < 0).any():
            raise ValueError(f"Invalid {col}")
    if (tasks.percent_complete > 100).any():
        raise ValueError("Percent complete exceeds 100")
    if not np.isfinite(pd.to_numeric(links.lag, errors="coerce")).all():
        raise ValueError("Invalid lag")
    for r in tasks.itertuples():
        for field in ["actual_start", "actual_finish", "constraint_date"]:
            value = getattr(r, field)
            if value:
                try:
                    if not np.is_busday(str(value)):
                        raise ValueError("Date is not a working day")
                except Exception as e:
                    raise ValueError(f"Invalid {field} for {r.id}: {value}") from e
        if r.constraint != "ASAP" and not r.constraint_date:
            raise ValueError(f"Missing constraint date: {r.id}")
        if r.percent_complete == 100 and (not r.actual_finish or not r.actual_start or r.remaining != 0):
            raise ValueError(f"Completed task requires actual dates and zero remaining: {r.id}")
        if 0 < r.percent_complete < 100 and (not r.actual_start or r.actual_finish):
            raise ValueError(f"In-progress actuals inconsistent: {r.id}")
        if r.percent_complete == 0 and r.actual_finish:
            raise ValueError(f"Not-started task has actual finish: {r.id}")
    g = nx.DiGraph()
    g.add_nodes_from(tasks.id)
    g.add_edges_from(zip(links.pred, links.succ))
    if not nx.is_directed_acyclic_graph(g):
        raise ValueError("Dependency cycle: "+str(nx.find_cycle(g)))
    return g

def solve(tasks, links, deadline=None, status=STATUS, remaining_override=None, statusing=True):
    """Forward/backward passes with FS, SS, FF and SF start-node weights.

    SS/FF cannot alone define a start-to-finish path through a task. Critical
    classification uses unconstrained late-start slack; deadline slack is separate.
    """
    g = validate(tasks, links)
    rows = tasks.set_index("id").to_dict("index")
    order = list(nx.topological_sort(g))
    t0 = day(status)
    incoming = {i: [] for i in order}
    outgoing = {i: [] for i in order}
    for e in links.itertuples():
        incoming[e.succ].append((e.pred, e.type, float(e.lag)))
        outgoing[e.pred].append((e.succ, e.type, float(e.lag)))
    es, ef, duration = {}, {}, {}
    weights = {}
    for i in order:
        r = rows[i]
        rem = (remaining_override or {}).get(i, r["remaining"])
        if not statusing:
            d, lower, fixed = float(r["duration"]), 0., None
        elif r["percent_complete"] == 100:
            fixed = float(day(r["actual_start"]))
            d = float(day(r["actual_finish"])) - fixed
            lower = fixed
        elif r["actual_start"]:
            fixed = float(day(r["actual_start"]))
            d = max(0, t0-fixed) + float(rem)
            lower = fixed
        else:
            fixed, d, lower = None, float(rem), float(t0)
        if r["constraint_date"] and r["constraint"] in {"SNET", "MSO", "FNET", "MFO"}:
            lower = max(lower, day(r["constraint_date"]) - (d if r["constraint"] in {"FNET", "MFO"} else 0))
        duration[i] = d
        candidates = [lower]
        for p, typ, lag in incoming[i]:
            w = {"FS":duration[p]+lag, "SS":lag, "FF":duration[p]-d+lag, "SF":-d+lag}[typ]
            weights[(p,i,typ)] = w
            candidates.append(es[p]+w)
        es[i] = fixed if fixed is not None else max(candidates)
        ef[i] = es[i]+d
    finish = max(ef.values())
    def backward(target, upper_constraints):
        ls = {i: target-duration[i] for i in order}
        for i in reversed(order):
            r = rows[i]
            if upper_constraints and r["constraint_date"]:
                c = day(r["constraint_date"])
                if r["constraint"] in {"SNLT", "MSO"}: ls[i] = min(ls[i],c)
                if r["constraint"] in {"FNLT", "MFO"}: ls[i] = min(ls[i],c-duration[i])
            for j,typ,lag in outgoing[i]:
                # A successor with actual start cannot be shifted in planning.
                bound = min(ls[j],es[j]) if statusing and rows[j]["actual_start"] else ls[j]
                ls[i] = min(ls[i],bound-weights[(i,j,typ)])
        return ls
    natural = backward(finish,False)
    required = backward(float(deadline) if deadline is not None else finish,True)
    result = tasks.copy()
    result["start_day"] = result.id.map(es)
    result["finish_day"] = result.id.map(ef)
    result["current_start"] = result.start_day.map(date_at)
    result["current_finish"] = result.finish_day.map(date_at)
    result["network_float"] = [natural[i]-es[i] for i in result.id]
    result["total_float"] = [required[i]-es[i] for i in result.id]
    result["late_start_day"] = result.id.map(required)
    result["late_finish_day"] = [required[i]+duration[i] for i in result.id]
    # Completed tasks have historical status, not actionable float.
    result["path_status"] = ["Complete" if rows[i]["percent_complete"]==100 else "Critical" if abs(natural[i]-es[i])<1e-7 else "Near-critical" if natural[i]-es[i]<=10 else "Noncritical" for i in result.id]
    return result, finish

def resource_load(schedule, assignments, resources, status=STATUS):
    """Uniform assignment FTE per active business day, clipped to status date."""
    records=[]
    idx=schedule.set_index("id")
    capacity=resources.set_index("resource_id").capacity_fte.to_dict()
    for a in assignments.itertuples():
        if a.task_id not in idx.index or a.resource_id not in capacity:
            raise ValueError("Unknown assignment task or resource")
        if a.units <= 0: raise ValueError("Assignment units must be positive")
        r=idx.loc[a.task_id]
        if r.percent_complete==100: continue
        for d in range(max(day(status),int(r.start_day)),int(math.ceil(r.finish_day))):
            records.append([a.resource_id,d,a.task_id,float(a.units)])
    raw=pd.DataFrame(records,columns=["resource_id","day","task_id","units"])
    if raw.empty: return pd.DataFrame(columns=["resource_id","day","demand_fte","task_ids","capacity_fte","excess_fte","date"])
    load=raw.groupby(["resource_id","day"]).agg(demand_fte=("units","sum"),task_ids=("task_id",lambda x:";".join(sorted(set(x))))).reset_index()
    load["capacity_fte"]=load.resource_id.map(capacity)
    load["excess_fte"]=(load.demand_fte-load.capacity_fte).clip(lower=0)
    load["date"]=load.day.map(date_at)
    return load
