import unittest
from pathlib import Path
import tempfile
import pandas as pd
from meridian.engine import solve,day,date_at,validate,resource_load
from meridian.analysis import simulate,diagnostics,health
from meridian.demo import generate

def tasks(durations):
    return pd.DataFrame([dict(id=f'T{i+1:03}',name=f'Task {i+1}',duration=d,remaining=d,percent_complete=0,actual_start='',actual_finish='',constraint='ASAP',constraint_date='',low_factor=1.,high_factor=1.,baseline_start='2026-04-06',baseline_finish='2026-04-20',current_start='2026-04-06',current_finish='2026-04-20') for i,d in enumerate(durations)])

def links(*edges):return pd.DataFrame(edges,columns=['pred','succ','type','lag'])
EMPTY_RISKS=pd.DataFrame(columns=['risk_id','probability','impact_low','impact_mode','impact_high','task_ids','status'])

class CalendarTests(unittest.TestCase):
    def test_weekend(self):self.assertEqual(date_at(5),'2026-04-13')
    def test_roundtrip(self):
        for d in [-3,0,1,20,500]:self.assertEqual(day(date_at(d)),d)
    def test_round_up(self):self.assertEqual(date_at(1.1),'2026-04-08')

class ScheduleTests(unittest.TestCase):
    def test_fs(self):
        r,f=solve(tasks([5,3]),links(('T001','T002','FS',0)),statusing=False)
        self.assertEqual(f,8);self.assertEqual(r.iloc[1].start_day,5)
    def test_ss(self):
        r,f=solve(tasks([5,3]),links(('T001','T002','SS',2)),statusing=False)
        self.assertEqual(f,5);self.assertEqual(r.iloc[1].start_day,2)
    def test_ff(self):
        r,f=solve(tasks([5,3]),links(('T001','T002','FF',1)),statusing=False)
        self.assertEqual(f,6);self.assertEqual(r.iloc[1].start_day,3)
    def test_sf(self):
        r,f=solve(tasks([5,3]),links(('T001','T002','SF',6)),statusing=False)
        self.assertEqual(r.iloc[1].finish_day,6)
    def test_deadline_float_not_network_float(self):
        r,_=solve(tasks([5,3]),links(('T001','T002','FS',0)),deadline=6,statusing=False)
        self.assertEqual(r.iloc[0].total_float,-2);self.assertEqual(r.iloc[0].network_float,0)
    def test_parallel_float(self):
        r,_=solve(tasks([10,3,0]),links(('T001','T003','FS',0),('T002','T003','FS',0)),statusing=False)
        self.assertEqual(r.iloc[1].network_float,7)
    def test_status_floor(self):
        r,_=solve(tasks([5]),links(),status='2026-04-20');self.assertEqual(r.iloc[0].start_day,10)
    def test_fixed_actual(self):
        t=tasks([5]);t.loc[0,['actual_start','actual_finish','remaining','percent_complete']]=['2026-04-06','2026-04-13',0,100]
        r,f=solve(t,links(),status='2026-04-20');self.assertEqual(f,5)
    def test_in_progress(self):
        t=tasks([10]);t.loc[0,['actual_start','remaining','percent_complete']]=['2026-04-06',4,60]
        r,f=solve(t,links(),status='2026-04-20');self.assertEqual(r.iloc[0].start_day,0);self.assertEqual(f,14)
    def test_hard_upper_does_not_force_finish(self):
        t=tasks([10]);t.loc[0,['constraint','constraint_date']]=['FNLT','2026-04-13']
        r,f=solve(t,links(),statusing=False);self.assertEqual(f,10);self.assertEqual(r.iloc[0].total_float,-5)
    def test_snet(self):
        t=tasks([3]);t.loc[0,['constraint','constraint_date']]=['SNET','2026-04-13']
        r,f=solve(t,links(),statusing=False);self.assertEqual(f,8)
    def test_cycle(self):
        with self.assertRaisesRegex(ValueError,'cycle'):validate(tasks([1,1]),links(('T001','T002','FS',0),('T002','T001','FS',0)))
    def test_unknown(self):
        with self.assertRaisesRegex(ValueError,'unknown'):validate(tasks([1]),links(('BAD','T001','FS',0)))
    def test_duplicate(self):
        t=tasks([1,1]);t.loc[1,'id']='T001'
        with self.assertRaisesRegex(ValueError,'Duplicate'):validate(t,links())
    def test_bad_duration(self):
        with self.assertRaisesRegex(ValueError,'duration'):validate(tasks([-1]),links())
    def test_invalid_date(self):
        t=tasks([1]);t.loc[0,['constraint','constraint_date']]=['SNET','not-date']
        with self.assertRaises(ValueError):validate(t,links())
    def test_resource_conflicts(self):
        t,_=solve(tasks([2,2]),links(),status='2026-04-06')
        a=pd.DataFrame([['T001','R',1],['T002','R',1]],columns=['task_id','resource_id','units']);r=pd.DataFrame([['R',1]],columns=['resource_id','capacity_fte'])
        load=resource_load(t,a,r,'2026-04-06');self.assertEqual(load.excess_fte.sum(),2)

class MonteCarloTests(unittest.TestCase):
    def test_deterministic_matches_cpm(self):
        t=tasks([5,3]);l=links(('T001','T002','FS',0));s,draws,_,_=simulate(t,l,EMPTY_RISKS,8,100,27,status='2026-04-06')
        self.assertTrue((draws.finish_day==8).all());self.assertEqual(s['on_time_probability'],1)
    def test_probability_one_risk(self):
        r=pd.DataFrame([dict(risk_id='R',probability=1,impact_low=4,impact_mode=4,impact_high=4,task_ids='T001',status='Open')])
        s,draws,_,_=simulate(tasks([5]),links(),r,8,100,27,status='2026-04-06');self.assertTrue((draws.finish_day==9).all())
    def test_completed_not_resampled(self):
        t=tasks([5]);t.loc[0,['actual_start','actual_finish','remaining','percent_complete']]=['2026-04-06','2026-04-13',0,100]
        s,d,_,_=simulate(t,links(),EMPTY_RISKS,5,100,27,status='2026-04-20');self.assertTrue((d.finish_day==5).all())
    def test_seed_and_quantiles(self):
        t=tasks([10]);t.high_factor=1.5;t.low_factor=.8
        a=simulate(t,links(),EMPTY_RISKS,12,100,7,status='2026-04-06');b=simulate(t,links(),EMPTY_RISKS,12,100,7,status='2026-04-06')
        pd.testing.assert_frame_equal(a[1],b[1]);self.assertGreaterEqual(a[0]['p80_day'],a[0]['p50_day'])

class DemoTests(unittest.TestCase):
    def test_demo_integrity_and_audit(self):
        with tempfile.TemporaryDirectory() as d:
            t,l=generate(d);validate(t,l);self.assertEqual(len(t),152);self.assertEqual(set(l.type),{'FS','SS','FF'})
            bad=pd.read_csv(Path(d)/'qa_bad_schedule.csv',keep_default_na=False);bl=pd.read_csv(Path(d)/'qa_bad_dependencies.csv',keep_default_na=False)
            found=set(diagnostics(bad,bl).check)
            self.assertTrue({'Unknown dependency','Self dependency','Cycle','Invalid date','Missing logic','Lead'}.issubset(found))
    def test_main_dates_consistent(self):
        with tempfile.TemporaryDirectory() as d:
            t,l=generate(d);issues=diagnostics(t,l)
            self.assertFalse(issues.check.isin(['Invalid sequencing','Invalid date','Cycle','Unknown dependency']).any())

if __name__=='__main__':unittest.main()
