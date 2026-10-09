"""Offline qualification of the three final native/preview case pairs."""
import json,hashlib,argparse
from pathlib import Path
from compare_movement_cases import PHASES,events
ROOT=Path(__file__).resolve().parents[2];base=ROOT/'reports/jade/movement-suite'
def local(p):return ROOT/p.replace('\\','/').split('rebge/')[-1]
original=json.loads((base/'stage43-final-original-audit-20261010.json').read_text())
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--comparison-prefix',default='stage43-final')
parser.add_argument('--output',type=Path,default=base/'stage43-final-paired-audit-20261010.json')
args=parser.parse_args()
def collapse(rows):
    out=[]
    for r in rows:
        if not out or out[-1]['action']!=r['action']:out.append(r)
    return out
def triggers(run):
    out=[];prev=None
    for e in run['events']:
        state=(abs(e['x'])+abs(e['y'])>.15,e['r2']>.5)
        if state!=prev:out.append(dict(t=e['performance_counter']-run['input_origin_performance_counter'],moving=state[0],r2=state[1]));prev=state
    return out
cases=[]
for case,label in [('run_held_start','held'),('run_to_walk','runwalk'),('reentry_gap_0.15','reentry')]:
    n=next(x for x in original['cases'] if x['case']==case)
    comparison=base/(args.comparison_prefix+'-'+label+'-comparison-20261010.json');comp=json.loads(comparison.read_text())
    pp=Path(comp['preview_run']);pr=json.loads(pp.read_text());nr=json.loads(Path(n['run']).read_text())
    preview=json.loads((pp.parent/'preview.json').read_text())
    prows=[]
    for r in preview:
        t=(r['unix_ns']-pr['input_origin_unix_ns'])/1e9
        if t<0:continue
        action=PHASES[r['phase']][0]
        prows.append(dict(t=t,action=action,phase=r['phase'],action_phase=r['action_phase'],speed=r['speed_byte'],strength=r['input_strength'],run_requested=r['run_requested'],blend=r['blend']))
    nrows=[dict(t=r['t'],action=r['A8'],phase=r['phase'],scalar48=r['scalar48'],mode=r['mode34'],speed=r['primary']['speed'],blend=r['blend'],AA=r['AA']) for r in n['samples'] if 0<=r['t']<=nr['case']['duration']]
    ne=collapse(nrows);pe=collapse(prows)
    # Initial waiting idle may have no native sample after input onset; readiness captures it independently.
    normalized_n=[r['action'] for r in ne if r['action']!=123];normalized_p=[r['action'] for r in pe if r['action']!=123]
    ntr=triggers(nr);ptr=triggers(pr);on_n=next(x['t'] for x in ntr if x['moving']);on_p=next(x['t'] for x in ptr if x['moving'])
    timing=[];used=set()
    for e in ne:
        match=next(((i,x) for i,x in enumerate(pe) if i not in used and x['action']==e['action']),None)
        if match:
            i,x=match;used.add(i);timing.append(dict(action=e['action'],native_t=e['t'],preview_t=x['t'],delta=x['t']-e['t'],from_move_onset_delta=(x['t']-on_p)-(e['t']-on_n)))
    pad=json.loads(local(pr['collectors'][0]['parsed']['report']).read_text());padchanges=[dict(t=pad['start_performance_counter']+x['elapsed_seconds']-pr['input_origin_performance_counter'],devices=x['devices']) for x in pad['winmm_rows']]
    cases.append(dict(case=case,status='material_startup_difference' if normalized_n!=normalized_p else 'material_action_chain_agrees_bounded',comparison=str(comparison),original_audit=n['trace'],preview_run=str(pp),preview_sha256=hashlib.sha256((pp.parent/'preview.json').read_bytes()).hexdigest(),native_events=ne,preview_events=pe,native_action_phase_events=comp['native_events'],preview_action_phase_events=comp['preview_events'],native_material_chain=normalized_n,preview_material_chain=normalized_p,timing=timing,native_command_triggers=ntr,preview_command_triggers=ptr,native_controller_changes=n['controller_changes'],preview_controller_changes=padchanges,raw_comparator_mismatches=comp['mismatches'],readiness=comp['setup_qualified'],qualification='Native jade_trace_consistency plus selector/action rereads; preview own frame observer; no atomic paired callback claim.'))
result=dict(schema='stage43-final-paired-audit-v1',cases=cases,findings=['Both R2 starts add preview Starting4 absent in native; native1->3->2 versus preview1->4->3->2. Preview running entry is approximately0.13s later even after command movement-onset alignment.','Held-run preview1->4 takes about0.201s; native mode2 already selected at neutral hold and native1->3 about0.175s. Fixed preview startup/dwell chain is a material branch difference.','Run-to-walk R2 release retains full scalar and delivers3 at nearly equal time; the earlier startup difference persists as a separate finding.','Reentry material chain1->4->3->0->51->4->3->0 agrees; pending AA1 and blend evidence are preserved in original audit. This does not certify universal restart51 row or full pose.'],limits=['Native3 phase1 retained in raw comparator and omitted only from action-level material comparison.','Initial123 omitted from native reentry post-onset samples is covered by readiness, not counted as material mismatch.','Sequential native read sampling and independent frame clocks bound all timing.','Different absolute terrain/initial facing; no actor displacement or diagnostic speed used to assert parity.','No full pose, collision, camera, procedural writer or whole game feel acceptance.','WinMM controller changes retain actual delivered axes/buttons; command timestamps are a separate clock.'])
result['comparison_prefix']=args.comparison_prefix
result['excluded_failed_runs']=[]
if args.comparison_prefix!='stage43-final':
    for path in base.glob('*-preview-r*-20261010-*/run.json'):
        run=json.loads(path.read_text())
        if run.get('status')=='failed':result['excluded_failed_runs'].append(dict(run=str(path),error=run.get('error'),exclusion='No qualified preview recording; retained but not substituted for selected successful case.'))
if args.comparison_prefix!='stage43-final':
    result['findings']=['Baseline startup differences are recorded in stage43-final-paired-audit-20261010.json; this report qualifies the selected comparison records independently.']
    for c in cases:
        result['findings'].append(c['case']+': '+c['status']+'; native '+str(c['native_material_chain'])+'; preview '+str(c['preview_material_chain'])+'.')
    baseline_path=base/'stage43-final-paired-audit-20261010.json'
    baseline=json.loads(baseline_path.read_text())
    result['baseline_audit']=str(baseline_path)
    result['baseline_sha256']=hashlib.sha256(baseline_path.read_bytes()).hexdigest()
    result['running_entry_changes']=[]
    for c in cases:
        old=next(x for x in baseline['cases'] if x['case']==c['case'])
        now=next((x for x in c['timing'] if x['action']==2),None)
        before=next((x for x in old['timing'] if x['action']==2),None)
        if now and before:result['running_entry_changes'].append(dict(case=c['case'],baseline_delta=before['from_move_onset_delta'],current_delta=now['from_move_onset_delta'],units='seconds after command movement onset; sample bounded'))
args.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps([dict(case=x['case'],status=x['status'],chains=[x['native_material_chain'],x['preview_material_chain']]) for x in cases]))
