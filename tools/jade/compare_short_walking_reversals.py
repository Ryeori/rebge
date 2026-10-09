"""Pair native short reverse observations with baseline preview action frames."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from compare_movement_cases import PHASES
from movement_suite import ROOT


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('native_audit',type=Path)
    p.add_argument('preview_runs',type=Path,nargs='+')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    native=json.loads(args.native_audit.read_text())
    cases=[]
    for path in args.preview_runs:
        run=json.loads(path.read_text())
        n=next(c for c in native['cases'] if c['case']==run['case']['id'])
        frames_path=path.parent/'preview.json'
        frames=json.loads(frames_path.read_text())
        for f in frames:
            f['t']=(f['unix_ns']-run['input_origin_unix_ns'])/1e9
        initial=next(f for f in frames if f['input_strength']>.35)
        command=next(e for e in run['events'] if e['x']>.6)
        ct=(command['unix_ns']-run['input_origin_unix_ns'])/1e9
        first=next(f for f in frames if f['t']>=ct and f['input_strength']>=.6
                   and dot(f['direction'],initial['direction'])<-.7)
        pre=next(f for f in reversed(frames) if f['t']<ct)
        events=[]
        for f in frames:
            state=PHASES[f['phase']]
            phase=f['action_phase'] if state[1] is None else state[1]
            if not events or (state[0],phase)!=(events[-1]['action'],events[-1]['phase']):
                events.append(dict(t=f['t'],action=state[0],phase=phase))
        def view(f):
            forward=[-f['actor_source_matrix'][i] for i in (4,5,6)]
            return dict(t=f['t'],phase=f['phase'],action_phase=f['action_phase'],norm=f['input_strength'],
                        dot_input=dot(forward,f['direction']),blend=f['blend'],native_speed_proxy=None)
        raw=json.loads(Path(n['source']).read_text())
        startup=[]
        for s in raw['samples']:
            t=raw['start_performance_counter']+s['elapsed_seconds']-json.loads((ROOT/n['run']).read_text())['input_origin_performance_counter']
            if not 0<=t<=n['command_opposite_t']+.1:
                continue
            heading=s.get('native_heading_inputs',{})
            selector=s.get('selector_inputs',{})
            speed=None
            fields=bytes.fromhex(selector.get('state_10c4_hex',''))
            if selector.get('unchanged') is True and len(fields)>=20:
                speed=struct.unpack_from('<f',fields,16)[0]
            velocity=None
            if heading.get('runtime_velocity_unchanged') is True:
                data=bytes.fromhex(heading['runtime_velocity_10_2b_hex'])
                vector=struct.unpack_from('<3f',data)
                scalar=struct.unpack_from('<f',data,24)[0]
                effective=[v*scalar for v in vector]
                velocity=dict(raw=list(vector),scalar=scalar,effective=effective,
                              magnitude=math.sqrt(dot(effective,effective)))
            startup.append(dict(t=t,index=s['index'],action=s['current_action_index_a8'],
                phase=s['current_phase_index'],speed10d4=speed,selector_stable=selector.get('unchanged'),
                actor_scalar48=selector.get('selection_value_48'),blend_active=selector.get('blend_active'),
                runtime_velocity=velocity,primary_header_stable=s.get('primary_header_unchanged'),
                primary_states_stable=s.get('primary_states_unchanged'),
                root_clocks=[dict(index=r['track_index'],elapsed=r['elapsed_seconds'],flags=r['track_flags'])
                    for r in s.get('primary_clip',{}).get('tracks',[]) if r['indexed_slot']==65535]))
        cases.append(dict(case=n['case'],native_run=n['run'],native_source_sha256=n['source_sha256'],
            preview_run=str(path),preview_run_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            preview_frames_sha256=hashlib.sha256(frames_path.read_bytes()).hexdigest(),
            native_events=[{k:e[k] for k in ('t','action','phase')} for e in n['qualified_events']],preview_events=events,
            native_pre=n['last_qualified_before_command'],native_opposite=n['first_qualified_opposite'],
            native_first_gate=n['first_open_angle_scalar_gate'],
            preview_command_t=ct,preview_pre=view(pre),preview_opposite=view(first),
            preview_outcome79=any(e['action']==79 for e in events),
            preview_outcome116=any(e['action'] in (116,117) and e['t']>=ct for e in events),
            native_outcome79=n['outcome79'],native_outcome116=n['outcome116_or117'],
            native_startup_separate_qualification=startup))
    result=dict(schema='paired-short-walking-reversal-v1',cases=cases,
        limits=['Preview trace does not expose the internal speed proxy; do not substitute actor displacement speed for native10D4.',
            'Startup velocity and selector rereads are separately qualified; primary clock markers are retained and do not establish writer order or blend weight.',
            'Same case commands do not prove matching initial world/camera geometry or device delivery.',
            'Native first qualified opposite is later than some actual native input callbacks.',
            'Actor scalar48 is not global norm. No smoothing mechanism is inferred from action timing alone.'])
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([dict(case=c['case'],native79=c['native_outcome79'],preview79=c['preview_outcome79'],
        native116=c['native_outcome116'],preview116=c['preview_outcome116'],
        native_firstgate=c['native_first_gate']['speed'],preview_firstopposite=c['preview_opposite'],
        preview_events=c['preview_events']) for c in cases]))


if __name__=='__main__':
    main()
