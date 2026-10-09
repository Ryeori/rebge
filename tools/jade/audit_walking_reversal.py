"""Qualify walking reversal selection and diagnostic continued displacement."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from movement_suite import ROOT
from audit_standing_turn_inputs import audit


def normalized(v):
    length=math.sqrt(sum(x*x for x in v))
    return [x/length for x in v]


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('run',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    observed=audit(args.run)
    run=json.loads(args.run.read_text())
    raw=json.loads(Path(observed['source']).read_text())
    samples={s['index']:s for s in raw['samples']}
    reverse=next(e for e in run['events'] if e['x']>.6 and e['elapsed']>1.)
    reverse_t=reverse['performance_counter']-run['input_origin_performance_counter']
    pre=next(r for r in reversed(observed['rows']) if r['t']<reverse_t)
    old_forward=normalized(pre['forward'])
    pre_pos=samples[pre['index']]['actor']['world_matrix'][12:15]
    after=[r for r in observed['rows'] if r['t']>=reverse_t]
    first_pos=samples[after[0]['index']]['actor']['world_matrix'][12:15]
    rows=[]
    for r in after:
        s=samples[r['index']]
        pos=s['actor']['world_matrix'][12:15]
        heading=s.get('native_heading_inputs',{})
        velocity=None
        if heading.get('runtime_velocity_unchanged') is True:
            velocity_raw=bytes.fromhex(heading['runtime_velocity_10_2b_hex'])
            v=list(struct.unpack_from('<3f',velocity_raw))
            scalar=struct.unpack_from('<f',velocity_raw,24)[0]
            velocity=dict(raw=v,scalar_28=scalar,effective=[x*scalar for x in v],
                          dot_old_forward=dot(v,old_forward)*scalar,
                          reread_stable=True)
        roots=[dict(track_index=t['track_index'],flags=t['track_flags'],
                    elapsed=t['elapsed_seconds'],frame_index=t['frame_index'])
               for t in s.get('primary_clip',{}).get('tracks',[])
               if t['indexed_slot']==65535]
        rows.append(dict(t=r['t'],action=r['action'],phase=r['phase'],norm=r['norm'],
            mode=r['mode'],speed=r['speed'],blend=r['blend_active'],dot_input=r['diagnostic_forward_dot'],
            actor_position=pos,source_root_clocks=roots,
            displacement_from_pre_dot_old=dot([x-y for x,y in zip(pos,pre_pos)],old_forward),
            displacement_from_first_post_dot_old=dot([x-y for x,y in zip(pos,first_pos)],old_forward),
            velocity=velocity,filter=r.get('direction_filter')))
    events=[]
    for r in observed['rows']:
        if not events or (r['action'],r['phase'])!=(events[-1]['action'],events[-1]['phase']):
            events.append({k:r[k] for k in ('t','action','phase','norm','mode','speed','blend_active')})
    early=[r for r in rows if r['t']<reverse_t+.65]
    peak=max(early,key=lambda r:r['displacement_from_first_post_dot_old'])
    stable_pre=[r for r in observed['rows'] if reverse_t-.4 <=r['t']<reverse_t]
    pad_path=next(Path(c['parsed']['report']) for c in run['collectors']
                  if 'probe_gamepad_input.py' in ' '.join(c['command']))
    if not pad_path.is_absolute():pad_path=ROOT/pad_path
    pad=json.loads(pad_path.read_text())
    delivery=[]
    for s in pad['winmm_rows']:
        t=pad['start_performance_counter']+s['elapsed_seconds']-run['input_origin_performance_counter']
        if reverse_t-.1<=t<=reverse_t+.15 and len(s['devices'])==1:
            d=s['devices'][0]
            delivery.append(dict(t=t,x=(d['x']-32767)/32768,y=(d['y']-32767)/32768))
    result=dict(schema='native-walking-reversal-audit-v1',run=str(args.run),
        run_sha256=hashlib.sha256(args.run.read_bytes()).hexdigest(),source=observed['source'],
        source_sha256=observed['source_sha256'],qualified=observed['qualified'],rejected=observed['rejected'],
        command_opposite=reverse,command_opposite_t=reverse_t,delivery_near_reverse=delivery,
        qualified_events=events,preturn=pre,
        steady_prequalified_count=len(stable_pre),
        steady_pre_action3=all(r['action']==3 for r in stable_pre),
        steady_pre_speed_range=[min(r['speed'] for r in stable_pre),max(r['speed'] for r in stable_pre)],
        reference_old_forward=old_forward,
        first_post_sample_t=after[0]['t'],
        maximum_early_continued_displacement=dict(t=peak['t'],source_units=peak['displacement_from_first_post_dot_old'],
            reference='first qualified POST-command actor position, so excludes pre-to-command unobserved motion'),
        early_rows=early,
        limits=['Sequential stable pose/selector/clock observations are not atomic callback inputs.',
            'Runtime velocity has independent reread qualification; its effective vector multiplies raw vector by scalar28 and does not establish writer order.',
            'Actor displacement in source units is diagnostic; terrain is qualified externally by screenshots, not this report.',
            'Positive old-direction displacement after the first native opposite-input sample demonstrates continued motion in this sampled interval; exact command onset and physical velocity zero time are bounded by sampling.',
            'Source-root clocks are independently captured primary tracks; agreement does not prove the entire pose.',
            'WinMM rows are change observations; absence of zero does not prove no sub-poll deadzone crossing.'])
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(output=str(args.output),reverse_t=reverse_t,steady3=result['steady_pre_action3'],
        steady_speed=result['steady_pre_speed_range'],peak=result['maximum_early_continued_displacement'],
        delivery=delivery,first_early_rows=[{k:r[k] for k in ('t','norm','action','displacement_from_first_post_dot_old','velocity')} for r in early[:5]])))


if __name__=='__main__':
    main()
