"""Compare source-coordinate actor drift after accepted opposite input."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def norm(v):
    length=math.sqrt(dot(v,v))
    return [x/length for x in v]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('native_audit',type=Path)
    parser.add_argument('preview_run',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    native=json.loads(args.native_audit.read_text())
    run=json.loads(args.preview_run.read_text())
    frames_path=args.preview_run.parent/'preview.json'
    frames=json.loads(frames_path.read_text())
    command=next(e for e in run['events'] if e['x']>.6 and e['elapsed']>1.)
    command_t=(command['unix_ns']-run['input_origin_unix_ns'])/1e9
    for frame in frames:
        frame['t']=(frame['unix_ns']-run['input_origin_unix_ns'])/1e9
    pre=next(f for f in reversed(frames) if f['t']<command_t)
    old_forward=norm([-pre['actor_source_matrix'][i] for i in (4,5,6)])
    # Direction is the preview's already accepted world input, not device command.
    post=next(f for f in frames if f['t']>=command_t and f['input_strength']>.6
              and dot(f['direction'],old_forward)<-.7)
    baseline=post['actor_source_matrix'][12:15]
    post_rows=[]
    for f in frames:
        if f['t']<post['t']:
            continue
        pos=f['actor_source_matrix'][12:15]
        post_rows.append(dict(t=f['t'],phase=f['phase'],action_phase=f['action_phase'],
            input_strength=f['input_strength'],direction=f['direction'],actor_position=pos,
            displacement_dot_old=dot([x-y for x,y in zip(pos,baseline)],old_forward),
            blend=f['blend']))
    enter80=next(r for r in post_rows if r['phase']=='TurnWalk')
    before80=[r for r in post_rows if r['t']<=enter80['t']]
    phase_events=[]
    for r in post_rows:
        state=(r['phase'],r['action_phase'])
        if not phase_events or state!=(phase_events[-1]['phase'],phase_events[-1]['action_phase']):
            phase_events.append({k:r[k] for k in ('t','phase','action_phase','displacement_dot_old')})
    output=dict(schema='walking-reversal-drift-comparison-v1',
        native_audit=str(args.native_audit),native_audit_sha256=hashlib.sha256(args.native_audit.read_bytes()).hexdigest(),
        preview_run=str(args.preview_run),preview_run_sha256=hashlib.sha256(args.preview_run.read_bytes()).hexdigest(),
        preview_frames_sha256=hashlib.sha256(frames_path.read_bytes()).hexdigest(),
        native_maximum_early_continued_displacement=native['maximum_early_continued_displacement'],
        preview_command_t=command_t,preview_first_accepted_opposite_t=post['t'],
        preview_first_opposite_dot=dot(post['direction'],old_forward),preview_reference_old_forward=old_forward,
        preview_maximum_until80=max(before80,key=lambda r:r['displacement_dot_old']),
        preview_minimum_until80=min(before80,key=lambda r:r['displacement_dot_old']),
        preview_maximum_all_post=max(post_rows,key=lambda r:r['displacement_dot_old']),
        preview_enter80=enter80,preview_phase_events=phase_events,
        preview_post_rows=post_rows,
        limits=['Native initial opposite dot is approximately -.985936 (170.4 degrees), preview angle is measured independently; this is a bounded drift comparison, not matched-geometry full parity.',
            'Both actor positions are source XYZ from own actor matrix. Neither Bevy mesh centroid nor metres are used.',
            'Each displacement reference is first qualified/accepted POST-input sample, not an interpolated command-time position. Native and preview omitted interval lengths differ.',
            'Preview wall-time frame stamps and native sequential reads do not establish identical simulation dt or callback order.',
            'Positive old-direction actor drift is desired inertia; this does not authorize removal of existing protection against mesh root jumps or imply all root offsets should accumulate.',
            'Native terrain and full pose are externally qualified, not proven by this report.'])
    args.output.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(output=str(args.output),native_peak=native['maximum_early_continued_displacement'],
        preview_first_opposite_t=post['t'],preview_dot=output['preview_first_opposite_dot'],
        preview_peak_until80=output['preview_maximum_until80'],preview_enter80=enter80,
        preview_peak_all=output['preview_maximum_all_post'],events=phase_events)))


if __name__=='__main__':
    main()
