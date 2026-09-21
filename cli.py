import argparse
import json
from pathlib import Path
import pandas as pd
from .demo import generate
from .engine import day,solve,resource_load
from .analysis import diagnostics,health,simulate

def read(path): return pd.read_csv(path,keep_default_na=False)

def run(data,out,trials=None,seed=None):
    data=Path(data);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    cfg=json.loads((data/'config.json').read_text())
    t=read(data/'schedule.csv');l=read(data/'dependencies.csv')
    a=read(data/'assignments.csv');r=read(data/'resources.csv');risks=read(data/'risks.csv')
    # Inspect the imported dates BEFORE replacing them with the network forecast.
    imported=diagnostics(t,l,cfg['status']);imported.to_csv(out/'import_diagnostics.csv',index=False)
    blocking=imported[imported.check.isin(['Unknown dependency','Cycle','Self dependency','Invalid relationship','Invalid date','Invalid sequencing'])]
    if len(blocking): raise ValueError('Invalid source schedule. See import_diagnostics.csv; forecast refused.')
    schedule,finish=solve(t,l,deadline=day(cfg['deadline']),status=cfg['status'])
    schedule['finish_variance']=[day(x)-day(y) for x,y in zip(schedule.current_finish,schedule.baseline_finish)]
    checks,issues=health(schedule,l,a,day(cfg['deadline']),cfg['status'])
    load=resource_load(schedule,a,r,cfg['status'])
    sra,draws,sensitivity,milestone_sra=simulate(t,l,risks,day(cfg['deadline']),trials or cfg['trials'],seed if seed is not None else cfg['seed'],cfg['status'])
    milestones=schedule[schedule.duration==0].copy().merge(milestone_sra,left_on='id',right_on='task_id')
    milestones['risk_status']=['Complete' if p==100 else 'Missed' if day(b)<day(cfg['status']) else 'At risk' if v>0 or prob<.8 else 'On track' for p,b,v,prob in zip(milestones.percent_complete,milestones.baseline_finish,milestones.finish_variance,milestones.on_baseline_probability)]
    risks['expected_impact_days']=risks.probability*(risks.impact_low+risks.impact_mode+risks.impact_high)/3
    summary=dict(program=cfg['program'],status=cfg['status'],tasks=len(t),work_activities=int(sum(t.duration>0)),milestones=int(sum(t.duration==0)),dependencies=len(l),completed=int(sum(t.percent_complete==100)),forecast_finish=schedule.current_finish.max(),baseline_finish=cfg['deadline'],slip_days=finish-day(cfg['deadline']),critical=int(sum(schedule.path_status=='Critical')),near_critical=int(sum(schedule.path_status=='Near-critical')),negative_float=int(sum((schedule.total_float<0)&(schedule.percent_complete<100))),at_risk_milestones=int(sum(milestones.risk_status.isin(['At risk','Missed']))),overloaded_resource_days=int(sum(load.excess_fte>0)),excess_fte_days=float(load.excess_fte.sum()),health_review=int(sum(checks.status=='REVIEW')),**sra)
    tables={'schedule_analysis':schedule,'health':checks,'diagnostics':issues,'resource_load':load,'resource_conflicts':load[load.excess_fte>0],'milestones':milestones,'risks':risks,'monte_carlo_trials':draws,'risk_sensitivity':sensitivity}
    for name,df in tables.items(): df.to_csv(out/f'{name}.csv',index=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    bundle={k:df.to_dict('records') for k,df in tables.items() if k!='monte_carlo_trials'}
    bundle.update(summary=summary,dependencies=l.to_dict('records'),assignments=a.to_dict('records'),resources=r.to_dict('records'),changes=read(data/'changes.csv').to_dict('records'),change_history=read(data/'change_history.csv').to_dict('records'))
    (out/'report_data.json').write_text(json.dumps(bundle,indent=2))
    from .exports import project_xml,tableau,figures,executive_report,html_dashboard
    project_xml(schedule,l,a,r,cfg,out.parent/'project'/'meridian.xml')
    tableau(out,out.parent/'bi')
    figures(schedule,load,risks,draws,summary,out)
    executive_report(summary,milestones,risks,checks,out/'executive_report.pdf')
    html_dashboard(bundle,out/'dashboard.html')
    print(json.dumps(summary,indent=2))

def main():
    p=argparse.ArgumentParser(description='MERIDIAN fictional schedule assurance')
    sub=p.add_subparsers(dest='command',required=True)
    gen=sub.add_parser('generate');gen.add_argument('--data',default='data')
    build=sub.add_parser('build');build.add_argument('--data',default='data');build.add_argument('--out',default='outputs');build.add_argument('--trials',type=int);build.add_argument('--seed',type=int)
    audit=sub.add_parser('audit');audit.add_argument('schedule');audit.add_argument('dependencies');audit.add_argument('--status',default='2026-09-18');audit.add_argument('--out',default='outputs/audit.csv')
    args=p.parse_args()
    if args.command=='generate': generate(args.data)
    elif args.command=='build': run(args.data,args.out,args.trials,args.seed)
    else:
        result=diagnostics(read(args.schedule),read(args.dependencies),args.status)
        Path(args.out).parent.mkdir(parents=True,exist_ok=True);result.to_csv(args.out,index=False)
        print(result.to_string(index=False))
        if len(result): raise SystemExit(1)

if __name__=='__main__':main()
