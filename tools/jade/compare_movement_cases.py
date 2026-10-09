"""Qualified action timing and actor diagnostics; never infer full-pose parity."""
import argparse
import json
import math
from pathlib import Path
from movement_suite import ROOT
from jade_trace_consistency import rejection_reasons

PHASES={'Idle':(0,0),'WaitingIdle':(123,0),'Slow':(1,0),'Restart':(51,0),
    'RestartSecond':(51,1),'Starting':(4,0),'Walking':(3,None),'Running':(2,None),
    'StandingNegative':(116,0),'StandingPositive':(117,0),'TurningA':(79,0),
    'TurningB':(79,1),'TurnWalk':(80,0),'RunStoppingA':(53,0),'RunStoppingB':(53,1),
    'StoppingA':(54,0),'StoppingB':(54,1)}

def events(rows):
    out=[]
    for r in rows:
        if not out or out[-1]['state']!=r['state']:
            out.append(dict(t=r['t'],state=r['state']))
    return out

def actor_metrics(rows):
    if len(rows)<2:return None
    points=[r['matrix'][12:15] for r in rows]
    distance=sum(math.dist(a,b) for a,b in zip(points,points[1:]))
    speeds=[]
    for a,b in zip(rows,rows[1:]):
        dt=b['t']-a['t']
        if dt>0:speeds.append(dict(t=b['t'],speed=math.dist(a['matrix'][12:15],b['matrix'][12:15])/dt))
    first,last=rows[0]['matrix'],rows[-1]['matrix']
    heading=math.atan2(-last[5],-last[4])-math.atan2(-first[5],-first[4])
    heading=math.atan2(math.sin(heading),math.cos(heading))
    return dict(net_displacement=math.dist(points[0],points[-1]),sampled_path_length=distance,
        final_heading_change_degrees=math.degrees(heading),peak_diagnostic_speed=max(s['speed'] for s in speeds),
        speed_samples=speeds,units='source units; native velocities use read wall time, preview uses simulation dt only in separate diagnostics')

def compare(native,preview):
    n=events(native);p=events(preview)
    mismatches=[]
    if [r['state'] for r in n]!=[r['state'] for r in p]:mismatches.append('action_phase_sequence')
    timing=[]
    used=set()
    for a in n:
        match=next(((i,b) for i,b in enumerate(p) if i not in used and b['state']==a['state']),None)
        if match:
            i,b=match;used.add(i)
            timing.append(dict(state=a['state'],native_t=a['t'],preview_t=b['t'],delta=b['t']-a['t']))
    return dict(native_events=n,preview_events=p,mismatches=mismatches,matched_sequence_timing=timing,
        native_actor=actor_metrics(native),preview_actor=actor_metrics(preview))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('native_run',type=Path);p.add_argument('preview_run',type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    n=json.loads(a.native_run.read_text());b=json.loads(a.preview_run.read_text())
    if n['case']['id']!=b['case']['id'] or n['case']['points']!=b['case']['points']:
        raise ValueError('Different case or input schedule')
    native_record=next(r['parsed']['report'] for r in n['collectors'] if 'capture_tracking_sequence.py' in ' '.join(r['command']))
    path=Path(native_record)
    if not path.is_absolute():path=ROOT/path
    raw=json.loads(path.read_text());nr=[];rejected=[]
    for s in raw['samples']:
        t=raw['start_performance_counter']+s['elapsed_seconds']-n['input_origin_performance_counter']
        if not 0<=t<=n['case']['duration']:continue
        reason=rejection_reasons(s)
        if reason:rejected.append(dict(index=s['index'],reasons=reason));continue
        nr.append(dict(t=t,state=[s['current_action_index_a8'],s['current_phase_index']],
            matrix=s['actor']['world_matrix'],speed_byte=s['primary_speed_byte']))
    br=[];unknown=[]
    for r in json.loads((a.preview_run.parent/'preview.json').read_text()):
        state=PHASES.get(r['phase'])
        if state is None:unknown.append(r['phase']);continue
        action,phase=state
        br.append(dict(t=(r['unix_ns']-b['input_origin_unix_ns'])/1e9,
            state=[action,r['action_phase'] if phase is None else phase],matrix=r['actor_source_matrix'],speed_byte=r['speed_byte']))
    result=compare(nr,br) if nr and br else dict(mismatches=['insufficient_samples'])
    readiness=[]
    for run in [n,b]:
        samples=run.get('readiness',[])
        state=samples[-1].get('state') if samples else None
        readiness.append(bool(state and state.get('action')==123 and not state.get('blend')
            and state.get('fresh') and state.get('input_norm') is not None
            and abs(state['input_norm'])<.01))
    controller_records=[]
    input_delivery=[]
    for run in [n,b]:
        controller_records.append([r.get('parsed',{}).get('report') for r in run['collectors']
            if 'probe_gamepad_input.py' in ' '.join(r['command'])])
        record=controller_records[-1][0]
        path=Path(record)
        if not path.is_absolute():path=ROOT/path
        pad=json.loads(path.read_text());values=[]
        for row in pad['winmm_rows']:
            t=pad['start_performance_counter']+row['elapsed_seconds']-run['input_origin_performance_counter']
            if not 0<=t<=run['case']['duration']:continue
            devices=row['devices']
            if len(devices)!=1:continue
            dev=devices[0]
            x=(dev['x']-32767)/32768
            values.append(dict(t=t,x=x,device=dev['index']))
        input_delivery.append(dict(target=run['parameters']['target'],observed_left_x=values,
            onset_x_015=next((v['t'] for v in values if abs(v['x'])>.15),None),
            full_x_090=next((v['t'] for v in values if abs(v['x'])>.90),None),
            limits='WinMM changed rows, single device required; X polarity only. Y/R2 delivery calibration remains separate.'))
    result.update(case=n['case']['id'],native_run=str(a.native_run),preview_run=str(a.preview_run),
        qualified_native=len(nr),rejected_native=rejected,preview_rows=len(br),unknown_preview_phases=sorted(set(unknown)),
        controller_records=controller_records,input_delivery=input_delivery,
        setup_qualified=readiness,status='needs_review' if all(readiness) else 'setup_unqualified',
        limits=['Action agreement does not prove full-pose agreement.',
                'No automatic PASS: inspect before/after terrain, actual controller input and source coverage.',
                'Read-time native speed can spike from mixed frames; do not equate peaks to game speed.',
                'TurnStop is unmapped until independently verified; such cases remain incomplete.',
                'Relative actor displacement requires matching camera/facing and sufficient sampling.'])
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(output=str(a.output),mismatches=result['mismatches'])))

if __name__=='__main__':main()
