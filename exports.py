"""Portable presentation/export formats. No commercial desktop application is required to build."""
from pathlib import Path
import json
import math
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from .engine import day,date_at

def put(parent,name,value):
    e=ET.SubElement(parent,name);e.text=str(value);return e

def project_xml(t,links,assignments,resources,cfg,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    p=ET.Element('Project',xmlns='http://schemas.microsoft.com/project')
    for k,v in [('SaveVersion',14),('Name','MERIDIAN M-27 - Fictional unclassified demo'),('Title','Aircraft development integrated schedule'),('ScheduleFromStart',1),('StartDate',cfg['start']+'T08:00:00'),('FinishDate',t.current_finish.max()+'T08:00:00'),('CalendarUID',1),('DefaultStartTime','08:00:00'),('DefaultFinishTime','17:00:00'),('MinutesPerDay',480),('MinutesPerWeek',2400),('DaysPerMonth',20),('StatusDate',cfg['status']+'T08:00:00')]:put(p,k,v)
    calendars=ET.SubElement(p,'Calendars');c=ET.SubElement(calendars,'Calendar')
    for k,v in [('UID',1),('Name','Standard - 8h Mon-Fri, no holidays'),('IsBaseCalendar',1),('BaseCalendarUID',-1)]:put(c,k,v)
    week=ET.SubElement(c,'WeekDays')
    for wd in range(1,8):
        w=ET.SubElement(week,'WeekDay');put(w,'DayType',wd);put(w,'DayWorking',int(2<=wd<=6))
        if 2<=wd<=6:
            periods=ET.SubElement(w,'WorkingTimes')
            for start,end in [('08:00:00','12:00:00'),('13:00:00','17:00:00')]:
                period=ET.SubElement(periods,'WorkingTime');put(period,'FromTime',start);put(period,'ToTime',end)
    nodes=ET.SubElement(p,'Tasks');uid={r.id:int(r.id[1:])+1000 for r in t.itertuples()};counter=0
    def dt(date,finish=False,milestone=False):
        if not finish or milestone:return date+'T08:00:00'
        return date_at(day(date)-1)+'T17:00:00'
    def add(row,outline,summary=False,custom_uid=None):
        nonlocal counter
        counter+=1;node=ET.SubElement(nodes,'Task')
        start=row['current_start'];finish=row['current_finish'];duration=day(finish)-day(start)
        vals=[('UID',custom_uid if summary else uid[row['id']]),('ID',counter),('Name',row['name']),('Type',1),('IsNull',0),('WBS',row['wbs']),('OutlineNumber',row['wbs']),('OutlineLevel',outline),('Start',dt(start)),('Finish',dt(finish,True,duration==0)),('Duration',f'PT{duration*8}H0M0S'),('DurationFormat',7),('Summary',int(summary)),('Milestone',int(duration==0 and not summary)),('PercentComplete',row.get('percent_complete',0))]
        for k,v in vals:put(node,k,v)
        if not summary:
            put(node,'ConstraintType',{'ASAP':0,'MSO':2,'MFO':3,'SNET':4,'SNLT':5,'FNET':6,'FNLT':7}[row['constraint']])
            if row['constraint_date']:put(node,'ConstraintDate',dt(row['constraint_date']))
            put(node,'CalendarUID',1)
            if row['actual_start']:put(node,'ActualStart',dt(row['actual_start']))
            if row['actual_finish']:put(node,'ActualFinish',dt(row['actual_finish'],True,row['duration']==0))
            put(node,'RemainingDuration',f"PT{int(row['remaining']*8)}H0M0S")
            put(node,'Notes','Fictional unclassified portfolio. Python dates use exclusive finish boundaries. Resource leveling is not applied.')
            for e in links[links.succ==row['id']].itertuples():
                dep=ET.SubElement(node,'PredecessorLink')
                for k,v in [('PredecessorUID',uid[e.pred]),('Type',{'FF':0,'FS':1,'SF':2,'SS':3}[e.type]),('CrossProject',0),('LinkLag',int(e.lag*4800)),('LagFormat',7)]:put(dep,k,v)
            base=ET.SubElement(node,'Baseline');put(base,'Number',0);put(base,'Start',dt(row['baseline_start']));put(base,'Finish',dt(row['baseline_finish'],True,row['duration']==0));put(base,'Duration',f"PT{(day(row['baseline_finish'])-day(row['baseline_start']))*8}H0M0S")
        return node
    add(t.iloc[0].to_dict(),1)
    phases=[p for p in t.phase.unique() if p!='Program']
    for phno,phase in enumerate(phases,1):
        phase_rows=t[t.phase==phase]
        add(dict(name=phase,wbs=str(phno),current_start=phase_rows.current_start.min(),current_finish=phase_rows.current_finish.max()),1,True,10000+phno)
        for wpno,wp in enumerate(phase_rows.work_package.unique(),1):
            block=phase_rows[phase_rows.work_package==wp]
            add(dict(name=wp,wbs=f'{phno}.{wpno}',current_start=block.current_start.min(),current_finish=block.current_finish.max()),2,True,20000+phno*100+wpno)
            for r in block.to_dict('records'):add(r,3)
    add(t.iloc[-1].to_dict(),1)
    rs=ET.SubElement(p,'Resources');rids={}
    for i,r in enumerate(resources.itertuples(),1):
        rids[r.resource_id]=i;node=ET.SubElement(rs,'Resource')
        for k,v in [('UID',i),('ID',i),('Name',r.name),('Type',1),('MaxUnits',r.capacity_fte),('CalendarUID',1)]:put(node,k,v)
    az=ET.SubElement(p,'Assignments')
    for i,a in enumerate(assignments.itertuples(),1):
        node=ET.SubElement(az,'Assignment')
        for k,v in [('UID',i),('TaskUID',uid[a.task_id]),('ResourceUID',rids[a.resource_id]),('Units',a.units)]:put(node,k,v)
    ET.indent(p);ET.ElementTree(p).write(path,encoding='utf-8',xml_declaration=True)

def tableau(out,bi):
    """Native editable TWB + packaged CSVs. Desktop rendering requires user validation."""
    out=Path(out);bi=Path(bi);bi.mkdir(parents=True,exist_ok=True);(bi/'Data').mkdir(exist_ok=True)
    t=pd.read_csv(out/'schedule_analysis.csv');risks=pd.read_csv(out/'risks.csv');load=pd.read_csv(out/'resource_load.csv');m=pd.read_csv(out/'milestones.csv');draws=pd.read_csv(out/'monte_carlo_trials.csv')
    phase=t[t.phase!='Program'].groupby('phase').finish_variance.max().reset_index();phase.columns=['label','value']
    risk=risks[['title','expected_impact_days']].sort_values('expected_impact_days',ascending=False);risk.columns=['label','value']
    load['ratio']=load.demand_fte/load.capacity_fte;capacity=load.groupby('resource_id').ratio.max().reset_index();capacity.columns=['label','value']
    gates=m[m.percent_complete<100][['wbs','finish_variance']].copy();gates.columns=['label','value']
    hist=draws.assign(week=pd.to_datetime(draws.finish_date).dt.to_period('W').astype(str)).groupby('week').size().reset_index(name='value');hist.columns=['label','value']
    sheets={'Phase finish slip (workdays)':phase,'Expected risk impact (workdays)':risk,'Peak demand to capacity ratio':capacity,'Milestone slip by WBS (workdays)':gates,'Completion trials by week':hist}
    wb=ET.Element('workbook',{'original-version':'18.1','source-build':'2023.1.0','source-platform':'win','version':'18.1','xmlns:user':'http://www.tableausoftware.com/xml/user'})
    put(wb,'document-format-change-manifest','')
    sources=ET.SubElement(wb,'datasources');ws=ET.SubElement(wb,'worksheets')
    for ix,(name,frame) in enumerate(sheets.items(),1):
        source=f'data{ix}';filename=f'{source}.csv';frame.to_csv(bi/'Data'/filename,index=False)
        ds=ET.SubElement(sources,'datasource',{'caption':name,'inline':'true','name':source,'version':'18.1'})
        connection=ET.SubElement(ds,'connection',{'class':'textscan','directory':'Data','filename':filename,'password':'','server':'','textscan-mode':'table'})
        relation=ET.SubElement(connection,'relation',{'name':filename,'table':f'[{filename}]','type':'table'})
        cols=ET.SubElement(relation,'columns',{'character-set':'UTF-8','header':'yes','locale':'en_US','separator':',','text-qualifier':'"'})
        ET.SubElement(cols,'column',{'datatype':'string','name':'label','ordinal':'0'})
        ET.SubElement(cols,'column',{'datatype':'real','name':'value','ordinal':'1'})
        for col,datatype,role,typ in [('label','string','dimension','nominal'),('value','real','measure','quantitative')]:ET.SubElement(ds,'column',{'datatype':datatype,'name':f'[{col}]','role':role,'type':typ})
        sheet=ET.SubElement(ws,'worksheet',{'name':name});table=ET.SubElement(sheet,'table');view=ET.SubElement(table,'view')
        dss=ET.SubElement(view,'datasources');ET.SubElement(dss,'datasource',{'caption':name,'name':source})
        dd=ET.SubElement(view,'datasource-dependencies',{'datasource':source})
        for col,datatype,role,typ in [('label','string','dimension','nominal'),('value','real','measure','quantitative')]:ET.SubElement(dd,'column',{'datatype':datatype,'name':f'[{col}]','role':role,'type':typ})
        ET.SubElement(dd,'column-instance',{'column':'[label]','derivation':'None','name':'[none:label:nk]','pivot':'key','type':'nominal'})
        ET.SubElement(dd,'column-instance',{'column':'[value]','derivation':'Sum','name':'[sum:value:qk]','pivot':'key','type':'quantitative'})
        ET.SubElement(view,'aggregation',{'value':'true'})
        ET.SubElement(table,'style')
        panes=ET.SubElement(table,'panes');pane=ET.SubElement(panes,'pane');ET.SubElement(pane,'view',{'breakdown':'auto'});ET.SubElement(pane,'mark',{'class':'Bar'})
        put(table,'rows',f'[{source}].[none:label:nk]');put(table,'cols',f'[{source}].[sum:value:qk]')
    dashboards=ET.SubElement(wb,'dashboards');dash=ET.SubElement(dashboards,'dashboard',{'name':'MERIDIAN Program Review'})
    ET.SubElement(dash,'style');ET.SubElement(dash,'size',{'maxheight':'1000','maxwidth':'1600','minheight':'1000','minwidth':'1600'})
    zones=ET.SubElement(dash,'zones')
    for ix,name in enumerate(list(sheets)[:4]):ET.SubElement(zones,'zone',{'h':'48000','id':str(ix+1),'name':name,'show-title':'true','type-v2':'sheet','w':'48000','x':str(1000+(ix%2)*50000),'y':str(1000+(ix//2)*50000)})
    windows=ET.SubElement(wb,'windows');ET.SubElement(windows,'window',{'class':'dashboard','name':'MERIDIAN Program Review'})
    ET.indent(wb);ET.ElementTree(wb).write(bi/'meridian.twb',encoding='utf-8',xml_declaration=True)
    with zipfile.ZipFile(bi/'meridian.twbx','w',zipfile.ZIP_DEFLATED) as z:
        z.write(bi/'meridian.twb','meridian.twb')
        for f in sorted((bi/'Data').glob('*.csv')):z.write(f,'Data/'+f.name)

def figures(t,load,risks,draws,s,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as md
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.labelcolor':'#24384b','text.color':'#122a40','figure.facecolor':'#f6f8fb','axes.facecolor':'white'})
    colors={'Engineering':'#3765a0','Software':'#14857a','Logistics':'#ad7c35','Testing':'#815ca4','Delivery':'#42754a'}
    fig,ax=plt.subplots(figsize=(14,6.5));rows=[]
    for phase in colors:
        x=t[t.phase==phase];rows.append((phase,x.baseline_start.min(),x.baseline_finish.max(),x.current_start.min(),x.current_finish.max()))
    for y,(phase,bs,bf,cs,cf) in enumerate(rows):
        ax.barh(y+.15,(pd.Timestamp(bf)-pd.Timestamp(bs)).days,left=md.date2num(pd.Timestamp(bs)),height=.18,color='#c6ced7')
        ax.barh(y-.10,(pd.Timestamp(cf)-pd.Timestamp(cs)).days,left=md.date2num(pd.Timestamp(cs)),height=.28,color=colors[phase])
    ax.set_yticks(range(5),colors);ax.invert_yaxis();ax.xaxis_date();ax.xaxis.set_major_formatter(md.DateFormatter('%b %Y'));ax.axvline(pd.Timestamp(s['status']),color='#d64c44',linestyle='--',label='Status date');ax.set_title('MERIDIAN M-27 | Phase schedule',loc='left',pad=20);ax.text(0,1.02,'Gray = approved baseline. Color = current forecast. Phase bars summarize overlapping work.',transform=ax.transAxes,color='#617386');ax.grid(axis='x',alpha=.15);fig.tight_layout();fig.savefig(out/'phase_schedule.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,5));ax.hist(draws.finish_day,bins=40,color='#3765a0',edgecolor='white');ax.set_xlabel('Business-day finish offset from 6 Apr 2026');ax.set_ylabel('Trials')
    for value,label,color in [(day(s['deadline']),'Deadline','#d64c44'),(s['p50_day'],'P50','#ad7c35'),(s['p80_day'],'P80','#14857a')]:ax.axvline(value,color=color,lw=2,label=f"{label}: {date_at(value)}")
    ax.legend();ax.set_title(f"Completion uncertainty | {s['trials']:,} seeded trials",loc='left');fig.tight_layout();fig.savefig(out/'completion_distribution.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,5));risk=risks.sort_values('expected_impact_days');ax.barh(risk.title,risk.expected_impact_days,color='#ad7c35');ax.set_xlabel('Probability x mean conditional impact (workdays)');ax.set_title('Risk register | Expected task-level impact',loc='left');fig.tight_layout();fig.savefig(out/'risk_exposure.png',dpi=160);plt.close(fig)

def executive_report(s,m,risks,checks,path):
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from matplotlib.font_manager import findfont,FontProperties
    pdfmetrics.registerFont(TTFont('ReportSans',findfont(FontProperties(family='DejaVu Sans'))))
    pdfmetrics.registerFont(TTFont('ReportSansBold',findfont(FontProperties(family='DejaVu Sans',weight='bold'))))
    pdfmetrics.registerFontFamily('ReportSans',normal='ReportSans',bold='ReportSansBold')
    c=canvas.Canvas(str(path),pagesize=(612,792));c.setTitle('MERIDIAN M-27 Executive Schedule Report')
    def text(x,y,w,content,size=10,color='#24384b',leading=None):
        style=ParagraphStyle('body',fontName='ReportSans',fontSize=size,leading=leading or size*1.45,textColor=HexColor(color));p=Paragraph(content,style);_,h=p.wrap(w,700);p.drawOn(c,x,y-h);return y-h
    def frame(page,title):
        c.setFillColor(HexColor('#122a40'));c.rect(0,692,612,100,fill=1,stroke=0)
        text(42,760,530,'MERIDIAN M-27',12,'#b6c9dd');text(42,735,530,title,23,'#ffffff')
        text(42,677,530,f"Status: {s['status']} | Fictional, unclassified portfolio demonstration",9)
        c.setStrokeColor(HexColor('#d4dce5'));c.line(42,44,570,44);text(42,33,510,'No real aircraft, contract, government or operational data. Forecast is not resource-leveled.',8);text(551,33,30,str(page),8)
    frame(1,'Executive schedule assessment')
    y=text(42,640,530,f"<b>Acceptance forecast: {s['forecast_finish']}</b>. The deterministic forecast is {s['slip_days']:.0f} workdays later than the {s['baseline_finish']} approved baseline. The risk model places P50 at <b>{s['p50_date']}</b> and P80 at <b>{s['p80_date']}</b>.",12)
    y=text(42,y-18,530,f"The schedule contains {s['tasks']} leaf activities and milestones, {s['dependencies']} dependency links and six resource pools. {s['completed']} items are complete. {s['critical']} unfinished items have zero network float. {s['at_risk_milestones']} future or missed milestones require attention.")
    c.drawImage(str(path.parent/'phase_schedule.png'),34,310,width=544,height=218,preserveAspectRatio=True,mask='auto')
    y=text(42,292,530,'<b>Management decisions</b>',13)
    y=text(42,y-8,530,'1. Review CR-002 before authorizing additional screening. Its duration impact remains outside the approved forecast.<br/>2. Confirm coverage for overloaded resource pools. Publish a leveled recovery scenario before committing to a new acceptance date.<br/>3. Preserve the original baseline. Record any future rebaseline as a separately approved version with an impact narrative.')
    y=text(42,y-15,530,f"<b>Schedule quality:</b> {s['health_review']} of 14 screening indicators need review. Mixed SS/FF links are intentional but require engineering justification. {s['overloaded_resource_days']} resource-days exceed capacity, totaling {s['excess_fte_days']:.1f} excess FTE-days. These are capacity signals, not a computed delay estimate.")
    c.showPage();frame(2,'Risk and assurance findings')
    c.drawImage(str(path.parent/'completion_distribution.png'),37,412,width=538,height=244,preserveAspectRatio=True,mask='auto')
    y=text(42,398,530,'<b>Highest expected task-level risks</b>',13)
    for r in risks.nlargest(3,'expected_impact_days').itertuples():
        y=text(42,y-7,530,f"<b>{r.title}</b>: {r.probability:.0%} probability, {r.impact_low}-{r.impact_high} conditional workdays. Owner: {r.owner}. Mitigation: {r.mitigation}.",10)
    y=text(42,y-16,530,'<b>How to interpret the forecast</b>',13)
    y=text(42,y-7,530,'The model samples triangular remaining durations and Bernoulli risk occurrences. Actual starts and finishes remain fixed. Each trial reschedules the dependency network. P80 means 80% of simulated completions occur by that date under the stated assumptions. It is not a contractual confidence guarantee.',10)
    y=text(42,y-12,530,'<b>Limitations:</b> No resource leveling, holidays, cost model or general duration correlation. Risk input ranges are fictional. Simulated impacts exclude already-realized issues in the current forecast. The 14-point screen uses documented demonstration thresholds and is not DCMA certification.',10)
    text(42,100,530,'Method references: GAO-16-89G, best practices 6-10 and Appendix VII (gao.gov/products/gao-16-89g). See docs/METHODOLOGY.md for exact definitions, denominators and native-app validation limits.',8)
    c.save()

def html_dashboard(bundle,path):
    template=(Path(__file__).parent/'dashboard_template.html').read_text()
    path.write_text(template.replace('__DATA__',json.dumps(bundle).replace('</','<\\/')))
