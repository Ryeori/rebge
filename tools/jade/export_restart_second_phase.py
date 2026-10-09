"""Add newly observed action51 phase1 without replacing other preview controls."""
import hashlib
import json
from pathlib import Path
from jade_trace_consistency import rejection_reasons
from match_sally_runtime_clip import signature
path=Path('reports/jade/stage43-tracking-sequence-20261009-185743.json')
clip=json.loads(Path('assets/animations/sally/local-samples/9E0004E6.json').read_text())
sample=next(s for s in json.loads(path.read_text())['samples'] if not rejection_reasons(s)
    and s['current_action_index_a8']==51 and s['current_phase_index']==1
    and signature(s['primary_clip']['tracks'],True)==signature(clip['tracks']))
tracks=[];roots=[];actors=[]
for t in sample['primary_clip']['tracks']:
    row=dict(index=t['track_index'],clock=dict(frames=t['frame_headers'],flags=t['track_flags'],auxiliary_short=t['auxiliary_short_u16']),
        state=dict(index=0,elapsed=0.,flags=5 if t['indexed_slot']==65535 else 1))
    if t['indexed_slot']==65535:
        if t['track_flags']&0x8000:actors.append(row)
    elif t['indexed_slot']==0:roots.append(row)
    else:tracks.append(row)
template=dict(key='9E0004E6',clip=clip,tracks=tracks,root_tracks=roots,actor_tracks=actors,speed=sample['primary_speed_byte'])
action=next(a for a in json.loads(Path('reports/jade/stage4-sally-actions.json').read_text())['actions'] if a['key']=='9E0004D3')
descriptor=dict(loop_phase=action['header_byte1'],phases=[dict(repeat_limit=r['bytes12_15'][0],speed_source_byte=r['bytes12_15'][2],flags=r['bytes12_15'][3]) for r in action['records']])
output=Path('assets/scenes/sally-playback/controlled.json');config=json.loads(output.read_text())
config['controls']['restart_second']=template;config['controls']['restart_descriptor']=descriptor
config['restart_second_provenance']=dict(source=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),sample=sample['index'],
    limits='Qualified phase1 clip and clocks. Manual slow-input sequence; not full pose or callback-time proof.')
output.write_text(json.dumps(config,separators=(',',':')))
print(json.dumps(dict(output=str(output),qualified_sample=sample['index'])))
