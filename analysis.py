"""Auditable schedule health, resource-independent risk simulation and diagnostics."""
import math
import numpy as np
import pandas as pd
import networkx as nx
from .engine import day, date_at, solve, validate, STATUS

def diagnostics(tasks,links,status=STATUS):
    issues=[]
    def add(check,task,detail): issues.append(dict(check=check,task_id=task,detail=detail))
    ids=set(tasks.id); idx=tasks.set_index('id')
    g=nx.DiGraph();g.add_nodes_from(ids)
    for e in links.itertuples():
        if e.pred not in ids or e.succ not in ids:
            add('Unknown dependency',e.succ,f'{e.pred} -> {e.succ}');continue
        g.add_edge(e.pred,e.succ)
        if e.pred==e.succ: add('Self dependency',e.succ,'Task depends on itself')
        if e.type not in {'FS','SS','FF','SF'}: add('Invalid relationship',e.succ,e.type);continue
        if e.lag<0: add('Lead',e.succ,f'{e.lag} workdays')
        p,s=idx.loc[e.pred],idx.loc[e.succ]
        try:
            left=day(s.current_start if e.type in {'FS','SS'} else s.current_finish)
            right=day(p.current_finish if e.type in {'FS','FF'} else p.current_start)+e.lag
            if left<right: add('Invalid sequencing',e.succ,f'{e.pred} {e.type}: {right-left:g} workdays short')
        except (ValueError,TypeError): add('Invalid date',e.succ,'Unparseable dependency date')
    if not nx.is_directed_acyclic_graph(g): add('Cycle','NETWORK',str(nx.find_cycle(g)))
    for r in tasks.itertuples():
        if r.percent_complete<100 and r.id not in {'T001','T152'} and (g.in_degree(r.id)==0 or g.out_degree(r.id)==0): add('Missing logic',r.id,'Missing predecessor or successor')
        if r.percent_complete<100 and r.duration>44: add('Excessive duration',r.id,f'{r.duration} > 44 workdays')
        if r.constraint in {'MSO','MFO','SNLT','FNLT'}: add('Hard constraint',r.id,r.constraint)
        if hasattr(r,'total_float') and r.percent_complete<100 and r.total_float<0: add('Negative float',r.id,f'{r.total_float:g} workdays')
        if hasattr(r,'path_status') and r.path_status in {'Critical','Near-critical'}: add(r.path_status,r.id,'Based on network float, not deadline float')
        try:
            if day(r.current_finish)<day(r.current_start): add('Invalid date',r.id,'Finish before start')
            if r.percent_complete<100 and day(r.current_finish)<day(status): add('Invalid date',r.id,'Incomplete finish before status')
            if r.percent_complete==0 and day(r.current_start)<day(status): add('Invalid date',r.id,'Unstarted work before status')
            for x in [r.actual_start,r.actual_finish]:
                if x and day(x)>day(status): add('Invalid date',r.id,'Future actual')
            if r.duration==0 and r.percent_complete<100 and day(r.baseline_finish)<day(status): add('Missed milestone',r.id,'Baseline gate date has passed')
        except (ValueError,TypeError): add('Invalid date',r.id,'Unparseable task date')
    return pd.DataFrame(issues,columns=['check','task_id','detail'])

def health(schedule,links,assignments,deadline,status=STATUS):
    issues=diagnostics(schedule,links,status)
    inc=schedule[(schedule.percent_complete<100)&(schedule.duration>0)]
    detail=schedule[schedule.duration>0]
    ids=set(inc.id)
    edges=links[links.succ.isin(schedule.loc[schedule.percent_complete<100,'id'])]
    planned=detail[detail.baseline_finish.map(day)<=day(status)]
    missed=planned[(planned.percent_complete<100)|(planned.current_finish>planned.baseline_finish)]
    rows=[]
    def ratio(no,name,n,d,threshold,direction='max',basis='Incomplete non-milestone activities'):
        value=float(n/d) if d else None
        passed=value is not None and (value<=threshold if direction=='max' else value>=threshold)
        rows.append(dict(point=no,indicator=name,numerator=int(n),denominator=int(d),value=value,threshold=threshold,direction=direction,status='N/A' if value is None else 'PASS' if passed else 'REVIEW',basis=basis))
    affected=lambda name:len(set(issues.loc[issues.check==name,'task_id'])&ids)
    ratio(1,'Missing logic',affected('Missing logic'),len(inc),.05)
    ratio(2,'Leads',sum(edges.lag<0),len(edges),0,basis='Relationships into incomplete tasks')
    ratio(3,'Lags',sum(edges.lag>0),len(edges),.05,basis='Relationships into incomplete tasks')
    ratio(4,'Finish-to-start relationships',sum(edges.type=='FS'),len(edges),.9,'min','Relationships into incomplete tasks')
    ratio(5,'Hard constraints',sum(inc.constraint.isin(['MSO','MFO','SNLT','FNLT'])),len(inc),.05)
    ratio(6,'High float',sum(inc.total_float>44),len(inc),.05)
    ratio(7,'Negative float',sum(inc.total_float<0),len(inc),0)
    ratio(8,'High duration',sum(inc.duration>44),len(inc),.05)
    ratio(9,'Invalid dates',affected('Invalid date'),len(inc),0)
    ratio(10,'Missing resources',len(ids-set(assignments.task_id)),len(inc),0)
    ratio(11,'Missed baseline tasks',len(missed),len(planned),.05,basis='Detail activities due by status, includes late completions')
    # Perturb a duration-driving activity by 600 business days. SS-only critical
    # starts may not drive duration, so test all eligible zero-float candidates.
    original=float(schedule.finish_day.max()); tests=[]
    for r in inc[inc.path_status=='Critical'].itertuples():
        _,shifted=solve(schedule,links,deadline=deadline,status=status,remaining_override={r.id:r.remaining+600})
        tests.append((r.id,shifted-original))
    passing=[x for x in tests if abs(x[1]-600)<1e-7]
    choice=passing[0] if passing else tests[0] if tests else ('NONE',0)
    ratio(12,'Critical path test',round(choice[1]),600,1,'min',f'Perturbed {choice[0]} by 600 workdays; exact 600-day response required')
    rows[-1]['status']='PASS' if abs(choice[1]-600)<1e-7 else 'REVIEW'
    length=original-day(status);tf=deadline-original
    rows.append(dict(point=13,indicator='Critical path length index',numerator=length+tf,denominator=length,value=(length+tf)/length if length>0 else None,threshold=.95,direction='min',status='N/A' if length<=0 else 'PASS' if (length+tf)/length>=.95 else 'REVIEW',basis='(Remaining calendar span + final deadline float) / remaining span; simplified CPLI'))
    ratio(14,'Baseline execution index',sum(detail.percent_complete==100),len(planned),.95,'min','All completed detail activities / detail activities baseline-due by status')
    return pd.DataFrame(rows),issues

def simulate(tasks,links,risks,deadline,trials=5000,seed=27,status=STATUS):
    if trials<100: raise ValueError('Use at least 100 trials')
    g=validate(tasks,links); order=list(nx.topological_sort(g)); idx=tasks.set_index('id')
    for r in risks.itertuples():
        if not 0<=r.probability<=1 or not 0<=r.impact_low<=r.impact_mode<=r.impact_high:
            raise ValueError('Invalid risk probability or impact bounds')
        if set(r.task_ids.split(';'))-set(tasks.id): raise ValueError('Unknown risk task')
    rng=np.random.default_rng(seed);remaining={};occurrences={}
    for r in tasks.itertuples():
        if not 0<=r.low_factor<=1<=r.high_factor: raise ValueError('Duration bounds must bracket mode')
        lo,mode,hi=r.remaining*r.low_factor,r.remaining,r.remaining*r.high_factor
        remaining[r.id]=np.full(trials,mode,dtype=float) if hi==lo else rng.triangular(lo,mode,hi,trials)
    for r in risks.itertuples():
        if r.status!='Open': continue
        occurrence=rng.random(trials)<r.probability;occurrences[r.risk_id]=occurrence
        impact=np.full(trials,r.impact_mode) if r.impact_high==r.impact_low else rng.triangular(r.impact_low,r.impact_mode,r.impact_high,trials)
        # A shared occurrence is applied to every mapped task: explicit correlation.
        for target in r.task_ids.split(';'):
            if idx.loc[target,'percent_complete']<100: remaining[target]+=occurrence*impact
    incoming={i:[] for i in order}
    for e in links.itertuples(): incoming[e.succ].append(e)
    es={};ef={};d={};sd=day(status)
    for i in order:
        r=idx.loc[i]
        if r.percent_complete==100:
            es[i]=np.full(trials,day(r.actual_start),dtype=float);ef[i]=np.full(trials,day(r.actual_finish),dtype=float);d[i]=ef[i]-es[i];continue
        if r.actual_start:
            es[i]=np.full(trials,day(r.actual_start),dtype=float);d[i]=sd-day(r.actual_start)+remaining[i];ef[i]=es[i]+d[i];continue
        d[i]=remaining[i];lower=np.full(trials,sd,dtype=float)
        if r.constraint_date and r.constraint in {'SNET','MSO','FNET','MFO'}:
            lower=np.maximum(lower,day(r.constraint_date)-(d[i] if r.constraint in {'FNET','MFO'} else 0))
        for e in incoming[i]:
            candidate={'FS':ef[e.pred]+e.lag,'SS':es[e.pred]+e.lag,'FF':ef[e.pred]+e.lag-d[i],'SF':es[e.pred]+e.lag-d[i]}[e.type]
            lower=np.maximum(lower,candidate)
        es[i]=lower;ef[i]=lower+d[i]
    finish=np.maximum.reduce(list(ef.values()))
    # Right-continuous empirical quantiles, then round UP to workday boundaries.
    p50,p80=np.quantile(finish,[.5,.8],method='higher')
    summary=dict(trials=trials,seed=seed,p50_day=float(p50),p80_day=float(p80),p50_date=date_at(p50),p80_date=date_at(p80),deadline=date_at(deadline),on_time_probability=float(np.mean(finish<=deadline)),mean_day=float(finish.mean()))
    trials_df=pd.DataFrame({'trial':range(1,trials+1),'finish_day':finish,'finish_date':[date_at(x) for x in finish]})
    sensitivity=[]
    for key,event in occurrences.items():
        difference=float(finish[event].mean()-finish[~event].mean()) if event.any() and (~event).any() else 0
        sensitivity.append(dict(risk_id=key,conditional_finish_difference=difference,occurrence_rate=float(event.mean())))
    milestone_rows=[]
    for r in tasks[tasks.duration==0].itertuples():
        a,b=np.quantile(ef[r.id],[.5,.8],method='higher')
        milestone_rows.append(dict(task_id=r.id,p50_date=date_at(a),p80_date=date_at(b),on_baseline_probability=float(np.mean(ef[r.id]<=day(r.baseline_finish)))))
    return summary,trials_df,pd.DataFrame(sensitivity),pd.DataFrame(milestone_rows)
