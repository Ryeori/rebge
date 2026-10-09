"""Add qualified reverse-input source clips; selection remains preview policy."""
import json
import hashlib
from project_paths import ASSET_ROOT, report_path
from jade_trace_consistency import rejection_reasons
from match_sally_runtime_clip import signature

paths=[report_path('stage43-tracking-sequence-20261009-'+s+'.json') for s in ('171056','171809')]
samples=[s for p in paths for s in json.loads(p.read_text())['samples']]
def template(key):
    clip=json.loads((ASSET_ROOT/f'animations/sally/local-samples/{key}.json').read_text())
    sample=next(s for s in samples if not rejection_reasons(s) and
        signature(s['primary_clip']['tracks'],True)==signature(clip['tracks']))
    tracks=[]; roots=[]; actors=[]
    for t in sample['primary_clip']['tracks']:
        row=dict(index=t['track_index'],clock=dict(frames=t['frame_headers'],flags=t['track_flags'],auxiliary_short=t['auxiliary_short_u16']),
            state=dict(index=0,elapsed=0.,flags=5 if t['indexed_slot']==65535 else 1))
        if t['indexed_slot']==65535:
            if t['track_flags']&0x8000:actors.append(row)
        elif t['indexed_slot']==0:roots.append(row)
        else:tracks.append(row)
    return dict(key=key,clip=clip,tracks=tracks,root_tracks=roots,actor_tracks=actors,speed=60)
actions=json.loads(report_path('stage4-sally-actions.json').read_text())['actions']
def descriptor(key):
    a=next(a for a in actions if a['key']==key)
    return dict(loop_phase=a['header_byte1'],phases=[dict(repeat_limit=r['bytes12_15'][0],speed_source_byte=r['bytes12_15'][2],flags=r['bytes12_15'][3]) for r in a['records']])
path=ASSET_ROOT/'scenes/sally-playback/controlled.json'
config=json.loads(path.read_text())
config['controls']['turn']=dict(a=template('7100B589'),b=template('7100B58B'),
    stop=template('7100B5E5'),walk=template('7100B5E7'),descriptor=descriptor('7100B58E'))
config['turn_provenance']=dict(inputs=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths],
    limits='Source clips and root publication qualified; raw opposite-direction threshold and completion request scheduling are preview policies, not recovered native VM predicates.')
path.write_text(json.dumps(config,separators=(',',':')))
print(path)
