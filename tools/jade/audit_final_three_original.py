"""Offline bounded final-three audit; no live game access."""
import json, struct, collections, hashlib
from pathlib import Path
from jade_trace_consistency import rejection_reasons
ROOT=Path(__file__).resolve().parents[2]
def local(p):
    return ROOT / p.replace('\\','/').split('rebge/')[-1]
def f32(h): return struct.unpack('<f',bytes.fromhex(h))[0]
def clock(clip):
    if not clip or len(clip.get('tracks',[]))<2:return None
    tr=clip['tracks'][1];ticks=[x['tick_raw'] for x in tr.get('frame_headers',[])];frame=tr['frame_index']
    return dict(controlling_track=1,frame=frame,elapsed=tr['elapsed_seconds'],ticks=ticks,source_clock=sum(ticks[:frame])/60+tr['elapsed_seconds'],limits='Track1 clock only; not whole source or pose parity.')
def header(h):
    b=bytes.fromhex(h)
    return dict(raw_hex=h,speed=b[2],action=struct.unpack_from('<H',b,0x54)[0],phase=b[0x56],byte57=b[0x57],flags58=b[0x58],duration_byte59=b[0x59],counter5a=struct.unpack_from('<H',b,0x5a)[0],blend_duration_seconds=(b[0x59]+1)/60,blend_counter_seconds=struct.unpack_from('<H',b,0x5a)[0]/15360)
def audit(path):
    run=json.loads(path.read_text()); tracepath=local(run['collectors'][0]['parsed']['report']);trace=json.loads(tracepath.read_text())
    controller=local(run['collectors'][1]['parsed']['report']);ctrl=json.loads(controller.read_text())
    origin=run['input_origin_performance_counter']; rejected=collections.Counter();rows=[]
    for s in trace['samples']:
        reasons=rejection_reasons(s)
        if reasons: rejected.update(reasons);continue
        sel=s['selector_inputs'];stat=s['stationary_selector_inputs']
        if not sel.get('unchanged') or not stat.get('unchanged') or not s.get('action_selection_unchanged'):rejected.update(['selector_or_action_changed']);continue
        t=trace['start_performance_counter']+s['elapsed_seconds']-origin
        ev=[e for e in run['events'] if e['performance_counter']<=origin+t];inp=ev[-1] if ev else None
        ph=header(s['primary_header_hex']);out=header(s['transition_header_hex']) if s.get('transition_header_hex') else None
        ph['clock']=clock(s['primary_clip'])
        if out:out['clock']=clock(s.get('transition_clip'))
        rows.append(dict(index=s['index'],t=t,input_command={k:inp[k] for k in ('elapsed','x','y','r2')} if inp else None,A8=s['current_action_index_a8'],AA=s['requested_action_index_aa'],A0=s['pending_transition_address_a0'],phase=s['current_phase_index'],scalar48=sel['selection_value_48'],mode34=stat['mode_34'],table=sel['actions_04_30'],blend=sel['blend_active'],primary_disabled=sel['primary_disabled'],exception=sel['exception_flags'],last10c4=stat['last_action_10c4'],selected1124=stat['selected_action_1124'],primary=ph,outgoing=out,dt=s['delta_time'],component_delta=s['component_delta_b8'],source_marker_f32=f32(s['primary_marker_before']),global_animation_context=s['native_heading_time_scale_inputs']['flag_1419a0290'],raw_norm=f32(s['native_heading_norm_inputs']['norm_hex']),descriptor=s['primary_phase_descriptor'],standing=s['standing_turn_inputs'],filter=s['native_direction_filter_inputs']))
    chains=[];prev=None
    for r in rows:
        sig=(r['A8'],r['phase'],r['AA'],r['blend'],r['mode34'])
        if sig!=prev:chains.append({k:r[k] for k in ('index','t','A8','phase','AA','blend','mode34','scalar48','last10c4','selected1124','primary','outgoing')});prev=sig
    changes=[];old=None
    for r in ctrl.get('winmm_rows',[]):
        sig=r.get('devices')
        if sig!=old:changes.append(dict(t=ctrl['start_performance_counter']+r['elapsed_seconds']-origin,devices=sig));old=sig
    return dict(case=run['case']['id'],run=str(path),trace=str(tracepath),controller=str(controller),hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (path,tracepath,controller)},status='qualified_sequential_sample_subset',collector_status=run['status'],qualified_count=len(rows),total_count=len(trace['samples']),rejections=dict(rejected),controller_changes=changes,chain=chains,samples=rows,contamination=dict(unexpected_actions=[r['A8'] for r in rows if r['A8'] not in (0,1,2,3,4,51,54,123)],terrain='declared flat_open; no observed ledge/grab/fall action; screenshot and collision parity not established',geometry='No standing/moving reversal actions observed; exact initial camera geometry not certified by this audit'))
result=dict(schema='stage43-final-original-audit-v1',cases=[],limits=['Sequential reads do not prove atomic callbacks or writer order.','Source signature and phase evidence do not establish whole pose parity.','Command timestamps and independent WinMM changes are distinct from actor scalar48.','Transition lookup row, outgoing effective-delta provenance and source duration require additional evidence; no exact restart51 expectation.'])
for case in ('run_held_start','run_to_walk','reentry_gap_0.15'):
    paths=sorted((ROOT/'reports/jade/movement-suite').glob(case+'-original-r1-20261010-*/run.json'))
    if paths:result['cases'].append(audit(paths[-1]))
    else:result['cases'].append(dict(case=case,status='record_not_yet_available'))
conclusions={
 'run_held_start':['Neutral R2 selects mode2 before movement: t0.029 scalar0; first movement1 at0.371 scalar0.35.','Observed A8 chain123->1->3->2->54->0. Full scalar arrives while blend gate defers run2; sampled run entry0.809.','Mode2 start is not direct run2 and does not justify an artificial fixed walk dwell. Stop54 retains AA0 through phases0/1 before idle0.'],
 'run_to_walk':['Observed123->1->3->2->3->54->0. R2 release changes mode2->1 while raw/scalar remain1; direct observed run2->walk3 at1.339.','Incoming3 runtime speed60 at sampled bind then56; outgoing2 speed57, phase0, blend byte59=8 (.15s), inactive by1.490. Source clock values retained per track1; no constant61 assumption.'],
 'reentry_gap_0.15':['Observed123->1->4->3->0->51->4->3->0; neutral first binds idle0 directly, not stop54 in this record.','Return raw1/scalar0.35 at0.785 still has idle0 blend active; next qualified0.814 has Restart51 AA1/scalar0.399.','Restart51 delivers AA1 in a bounded unsampled interval; next observed4 at0.986 scalar0.921 then3 at1.164. This is observed51 evidence, not proof of a mandatory row for all reentries.']}
for c in result['cases']:c['conclusions']=conclusions[c['case']]
out=ROOT/'reports/jade/movement-suite/stage43-final-original-audit-20261010.json'
out.write_text(json.dumps(result,indent=2))
for c in result['cases']:print(json.dumps({k:v for k,v in c.items() if k not in ('samples','controller_changes')}))
