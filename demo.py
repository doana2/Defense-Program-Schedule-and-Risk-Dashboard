"""Deterministic fictional MERIDIAN M-27 flight-research demonstrator data."""
from pathlib import Path
import json
import pandas as pd
from .engine import solve, day, date_at, STATUS

PHASES = {
    "Engineering": ["Airframe definition", "Power and thermal", "Avionics architecture", "Structural substantiation", "Prototype integration", "Design acceptance"],
    "Software": ["Platform services", "Telemetry collection", "Health monitoring", "Operator interface", "Integration build", "Release qualification"],
    "Logistics": ["Supplier qualification", "Long lead procurement", "Spares provisioning", "Maintenance planning", "Training development", "Support readiness"],
    "Testing": ["Bench verification", "Environmental qualification", "Ground integration", "Taxi readiness", "Flight research campaign", "Test evidence closure"],
    "Delivery": ["Configuration freeze", "Documentation release", "Acceptance inspection", "Operator training", "Transfer preparation", "Program closeout"],
}
VERBS={
    "Engineering":["Define requirements","Develop design","Review analysis","Resolve findings","Approval gate"],
    "Software":["Specify interfaces","Implement module","Verify integration","Close defects","Release gate"],
    "Logistics":["Define support needs","Prepare support package","Review readiness","Resolve shortages","Readiness gate"],
    "Testing":["Prepare procedure","Execute evaluation","Analyze results","Close discrepancies","Evidence gate"],
    "Delivery":["Plan handover","Prepare deliverables","Verify acceptance","Close actions","Acceptance gate"]}

def generate(root):
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    tasks=[]; links=[]; assignments=[]
    def task(i,wbs,name,phase,wp,dur):
        tasks.append(dict(id=i,wbs=wbs,name=name,phase=phase,work_package=wp,duration=dur,remaining=dur,percent_complete=0,actual_start="",actual_finish="",constraint="ASAP",constraint_date="",notes="Fictional planning estimate",low_factor=.85,high_factor=1.25))
    task("T001","0","Program authorization","Program","Authorization",0)
    gates={}; first={}; n=2
    for phno,(phase,packages) in enumerate(PHASES.items(),1):
        for wpno,wp in enumerate(packages,1):
            ids=[f"T{x:03}" for x in range(n,n+5)]
            first[(phase,wpno)]=ids[0]; gates[(phase,wpno)]=ids[-1]
            for k,i in enumerate(ids):
                duration=0 if k==4 else [8,14,10,7][k]+((phno+wpno)%3)
                task(i,f"{phno}.{wpno}.{k+1}",f"{wp}: {VERBS[phase][k]}",phase,wp,duration)
                if duration:
                    assignments.append(dict(task_id=i,resource_id=f"R{phno:02}",units=1.0))
                    if k in (2,3): assignments.append(dict(task_id=i,resource_id="R06",units=.5))
            edges=[(ids[0],ids[1],"SS",2),(ids[1],ids[2],"FS",0),(ids[0],ids[2],"FF",0),(ids[2],ids[3],"FS",0),(ids[0],ids[3],"FS",0),(ids[3],ids[4],"FS",0)]
            links.extend(dict(pred=p,succ=s,type=t,lag=l) for p,s,t,l in edges)
            n+=5
    for phase in PHASES:
        for wp in range(1,7):
            target=first[(phase,wp)]
            if wp>2: predecessors=[gates[(phase,wp-2)]]
            elif phase in {"Engineering","Logistics"}: predecessors=["T001"]
            elif phase=="Software": predecessors=[gates[("Engineering",wp)]]
            elif phase=="Testing": predecessors=[gates[(p,w)] for p in ["Engineering","Software"] for w in [5,6]]
            else: predecessors=[gates[(p,w)] for p in ["Testing","Logistics"] for w in [5,6]]
            links.extend(dict(pred=p,succ=target,type="FS",lag=0) for p in predecessors)
    task("T152","6","Final demonstrator acceptance","Program","Final acceptance",0)
    links.extend(dict(pred=gates[("Delivery",w)],succ="T152",type="FS",lag=0) for w in [5,6])
    t=pd.DataFrame(tasks); l=pd.DataFrame(links)
    base,baseline_finish=solve(t,l,statusing=False)
    t["baseline_start"]=base.current_start
    t["baseline_finish"]=base.current_finish
    # Keep baseline frozen. One approved scope change and one forecast issue.
    change_task=f"T{int(first[('Software',6)][1:])+1:03}"
    t.loc[t.id==change_task,"duration"]+=24
    issue_task=f"T{int(first[('Logistics',2)][1:])+1:03}"
    t.loc[t.id==issue_task,"duration"]=48
    t["remaining"]=t.duration
    executed,_=solve(t,l,statusing=False)
    sd=day(STATUS)
    for ix,r in executed.iterrows():
        if r.finish_day<=sd:
            t.loc[ix,["percent_complete","actual_start","actual_finish","remaining"]]=[100,r.current_start,r.current_finish,0]
        elif r.start_day<sd:
            remaining=r.finish_day-sd
            t.loc[ix,["percent_complete","actual_start","remaining"]]=[min(99,int((sd-r.start_day)/r.duration*100)),r.current_start,remaining]
    # At-risk deadline as upper bound; never force forecast to violate logic.
    t.loc[t.id=="T152",["constraint","constraint_date"]]=["FNLT",date_at(baseline_finish)]
    result,finish=solve(t,l,deadline=baseline_finish)
    t["current_start"]=result.current_start; t["current_finish"]=result.current_finish
    t.to_csv(root/"schedule.csv",index=False); l.to_csv(root/"dependencies.csv",index=False)
    pd.DataFrame(assignments).to_csv(root/"assignments.csv",index=False)
    pd.DataFrame([dict(resource_id=f"R{i:02}",name=n,capacity_fte=c) for i,(n,c) in enumerate([
        ("Design engineering team",1.5),("Software team",1.5),("Logistics team",2),("Test team",1.5),("Delivery team",2),("Quality review team",1)],1)]).to_csv(root/"resources.csv",index=False)
    risk_specs=[
        ("Avionics interface rework",.35,8,16,30,first[("Software",4)],"Software lead","Freeze interfaces and hold weekly integration reviews"),
        ("Environmental retest",.3,10,20,35,first[("Testing",2)],"Test lead","Run prequalification screening before chamber booking"),
        ("Instrument delivery delay",.25,8,15,25,first[("Testing",1)],"Supply lead","Qualify an alternate supplier"),
        ("Ground test discrepancy",.4,5,12,22,first[("Testing",3)],"Test lead","Add an early dry run"),
        ("Review team congestion",.4,3,8,15,first[("Engineering",6)],"Quality lead","Reserve named reviewers"),
        ("Training material revision",.2,4,8,16,first[("Delivery",4)],"Logistics lead","Pilot the training package"),
        ("Acceptance documentation gap",.3,3,7,12,first[("Delivery",3)],"Delivery lead","Perform an evidence completeness review"),
        ("Integration build regression",.35,5,12,24,first[("Software",5)],"Software lead","Automate regression tests"),
        ("Flight research weather window",.3,5,10,20,first[("Testing",5)],"Test lead","Reserve contingency windows"),
        ("Configuration discrepancy",.25,3,6,12,first[("Delivery",1)],"Configuration lead","Audit as-built records early"),
    ]
    risks=[]
    for i,(title,p,lo,mode,hi,target,owner,mitigation) in enumerate(risk_specs,1):
        risks.append(dict(risk_id=f"RISK-{i:02}",title=title,probability=p,impact_low=lo,impact_mode=mode,impact_high=hi,task_ids=target,owner=owner,mitigation=mitigation,status="Open",review_date=STATUS))
    pd.DataFrame(risks).to_csv(root/"risks.csv",index=False)
    changes=[
        dict(change_id="CR-001",task_id=change_task,field="duration",old_value=int(t.set_index('id').loc[change_task,'duration'])-24,new_value=int(t.set_index('id').loc[change_task,'duration']),status="Approved",requested="2026-08-24",decided="2026-08-28",owner="Program manager",reason="Expanded telemetry interface verification",applied=True),
        dict(change_id="CR-002",task_id=first[("Testing",2)],field="duration",old_value=8,new_value=13,status="Pending",requested="2026-09-14",decided="",owner="Test lead",reason="Additional environmental screening",applied=False),
        dict(change_id="CR-003",task_id="T152",field="deadline",old_value=date_at(baseline_finish),new_value=date_at(baseline_finish+20),status="Rejected",requested="2026-09-10",decided="2026-09-17",owner="Program manager",reason="Request to move acceptance commitment",applied=False),
    ]
    # Derive pending old value from source rather than assuming its duration.
    changes[1]['old_value']=int(t.set_index('id').loc[changes[1]['task_id'],'duration']); changes[1]['new_value']=changes[1]['old_value']+5
    pd.DataFrame(changes).to_csv(root/"changes.csv",index=False)
    history=[]
    for c in changes:
        history.append(dict(change_id=c['change_id'],timestamp=c['requested']+"T09:00:00",actor=c['owner'],from_status="Draft",to_status="Submitted",comment=c['reason']))
        if c['decided']: history.append(dict(change_id=c['change_id'],timestamp=c['decided']+"T15:00:00",actor="Fictional change control board",from_status="Submitted",to_status=c['status'],comment="Forecast update only. Original baseline remains frozen."))
    pd.DataFrame(history).to_csv(root/"change_history.csv",index=False)
    (root/"config.json").write_text(json.dumps(dict(program="MERIDIAN M-27",start="2026-04-06",status=STATUS,deadline=date_at(baseline_finish),seed=27,trials=5000,high_duration=44,high_float=44,near_critical=10,calendar="Monday-Friday, 8h/day, no holidays, exclusive finish"),indent=2))
    # Deliberately flawed vendor submission. Main analysis always uses clean data.
    fixture=t.copy()
    unfinished=fixture.index[fixture.percent_complete<100].tolist()
    fixture.loc[unfinished[0],"current_finish"]="2026-09-17"
    fixture.loc[unfinished[1],"current_start"]="2026-09-17"
    fixture.to_csv(root/"qa_bad_schedule.csv",index=False)
    bad=l.copy(); target=fixture.loc[unfinished[2],'id']; bad=bad[bad.succ!=target]
    bad.loc[len(bad)]={"pred":"UNKNOWN","succ":fixture.loc[unfinished[3],'id'],"type":"FS","lag":0}
    bad=pd.concat([bad,pd.DataFrame([dict(pred="T152",succ="T152",type="FS",lag=-3)])],ignore_index=True)
    bad.to_csv(root/"qa_bad_dependencies.csv",index=False)
    return t,l
