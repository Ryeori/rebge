"""Preserve preview bank and add qualified source standing turns 116/117."""
import json
import hashlib
from pathlib import Path
from jade_trace_consistency import rejection_reasons
from match_sally_runtime_clip import signature

inputs=[]
def template(action, key, stamp):
    path=Path(f'reports/jade/stage43-tracking-sequence-20261009-{stamp}.json')
    clip=json.loads(Path(f'assets/animations/sally/local-samples/{key}.json').read_text())
    sample=next(s for s in json.loads(path.read_text())['samples'] if not rejection_reasons(s)
        and s['current_action_index_a8']==action
        and signature(s['primary_clip']['tracks'],True)==signature(clip['tracks']))
    tracks=[];roots=[];actors=[]
    for t in sample['primary_clip']['tracks']:
        row=dict(index=t['track_index'],clock=dict(frames=t['frame_headers'],flags=t['track_flags'],auxiliary_short=t['auxiliary_short_u16']),
            state=dict(index=0,elapsed=0.,flags=5 if t['indexed_slot']==65535 else 1))
        if t['indexed_slot']==65535:
            if t['track_flags']&0x8000:actors.append(row)
        elif t['indexed_slot']==0:roots.append(row)
        else:tracks.append(row)
    inputs.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),sample=sample['index'],action=action,speed=sample['primary_speed_byte']))
    return dict(key=key,clip=clip,tracks=tracks,root_tracks=roots,actor_tracks=actors,speed=sample['primary_speed_byte'])

output=Path('assets/scenes/sally-playback/controlled.json')
config=json.loads(output.read_text())
config['controls']['standing_turn']=dict(negative=template(116,'26003A36','182845'),positive=template(117,'26003A85','171809'))
config['standing_turn_provenance']=dict(inputs=inputs,limits='Qualified source tracks and clocks; opposite-input threshold, entry blend and completion dispatch remain explicit preview policies. Not full native pose parity.')
output.write_text(json.dumps(config,separators=(',',':')))
print(json.dumps(dict(output=str(output),inputs=inputs)))
