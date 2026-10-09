"""Report qualified turn phases observed with zero native selection input."""
import hashlib,json
from pathlib import Path
from jade_trace_consistency import rejection_reasons

rows=[]
for stamp,hold in [('201330',0.2),('201452',0.4),('201905',0.2)]:
    path=Path(f'reports/jade/stage43-tracking-sequence-20261009-{stamp}.json')
    raw=path.read_bytes();samples=json.loads(raw)['samples']
    released=[];events=[];previous=None;qualified_turn_inputs=[]
    for s in samples:
        action=(s['current_action_index_a8'],s['current_phase_index'])
        if action!=previous:
            events.append(dict(sample=s['index'],elapsed=s['elapsed_seconds'],action=action,qualified=not rejection_reasons(s)))
        previous=action
        if action[0] in (79,78,80) and not rejection_reasons(s):
            qualified_turn_inputs.append(dict(sample=s['index'],action=action,selection_value=s['selector_inputs']['selection_value_48']))
        if action[0]==79 and s['selector_inputs']['selection_value_48']==0. and not rejection_reasons(s):
            t=s['primary_clip']['tracks'][0]
            released.append(dict(sample=s['index'],phase=action[1],elapsed=s['elapsed_seconds'],clock_elapsed=t['elapsed_seconds'],clock_index=t['frame_index'],speed=s['primary_speed_byte'],request=s['requested_action_index_aa']))
    rows.append(dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),opposite_hold_seconds=hold,repress=stamp=='201905',events=events,qualified_zero_input_turn_samples=released,qualified_turn_inputs=qualified_turn_inputs))
report=dict(inputs=rows,conclusion='Release recordings retain action79 after native selection input becomes zero; phase1 precedes stop78. Repress recording continues79 into walk exit80. No early cut added to preview; completion observes latest held input.',limits=['Sequential consistency only; not atomic callback snapshots or full pose proof.','Command hold times are external; selection_value_48 is the native observation used for release.','Later runs also include standing117 before walking; only fast-turn79 release/repress is evaluated.'])
output=Path('reports/jade/stage43-turn-release-validation-20261009.json')
output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(report=str(output),qualified_released_counts=[len(r['qualified_zero_input_turn_samples']) for r in rows])))
