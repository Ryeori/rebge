"""Add source running/stop clips. Preserve the existing controlled bank."""
import hashlib
import json
from pathlib import Path
from jade_trace_consistency import rejection_reasons
from match_sally_runtime_clip import signature

paths=[Path('reports/jade/stage43-tracking-sequence-20261009-'+s+'.json') for s in ('182845','183348','203116','213501')]
samples=[]; sample_sources={}; selected_templates={}
for p in paths:
    rows=json.loads(p.read_text())['samples']
    samples.extend(rows)
    sample_sources.update({id(s):str(p) for s in rows})
actions={a['key']:a for a in json.loads(Path('reports/jade/stage4-sally-actions.json').read_text())['actions']}
decoded=json.loads(Path('reports/jade/stage43-action-transition-decoded-20261009.json').read_text())['actions']
def template(key, observed=True):
    path=Path('assets/animations/sally/local-samples')/(key+'.json')
    clip=json.loads(path.read_text())
    candidates=[s for s in samples if not rejection_reasons(s)
        and signature(s['primary_clip']['tracks'],True)==signature(clip['tracks'])]
    # Stop53 uses the observed steady VM speed; the entry60 snapshot is a
    # separate descriptor binding event, not its persistent playback speed.
    sample=next((s for s in candidates if s['primary_speed_byte']==56
        and s['speed_writer_inputs']['unchanged']),None) if key in ('9E0004DD','9E0004DE') else next(iter(candidates),None)
    if observed and sample is None:raise ValueError('No qualified clip: '+key)
    if sample:
        selected_templates[key]=dict(path=sample_sources[id(sample)],sample=sample['index'],
            action=sample['current_action_index_a8'],phase=sample['current_phase_index'],
            speed=sample['primary_speed_byte'])
    tracks=[]; roots=[]; actors=[]
    for i,t in enumerate(clip['tracks']):
        native=sample['primary_clip']['tracks'][i] if sample else None
        clock=dict(frames=native['frame_headers'] if native else [dict(tick_raw=f['tick_raw'],flags=f['flags']|(4 if j==0 and t['short1']==65535 else 0)) for j,f in enumerate(t['frames'])],
            flags=native['track_flags'] if native else 32771, auxiliary_short=native['auxiliary_short_u16'] if native else 0)
        row=dict(index=i,clock=clock,state=dict(index=0,elapsed=0.,flags=5 if t['short1']==65535 else 1))
        if t['short1']==65535:
            if t['source_flags']&0x8000:actors.append(row)
        elif t['short1']==0:roots.append(row)
        else:tracks.append(row)
    return dict(key=key,clip=clip,tracks=tracks,root_tracks=roots,actor_tracks=actors,speed=sample['primary_speed_byte'] if sample else 60)
def descriptor(key):
    a=actions[key]
    return dict(loop_phase=a['header_byte1'],phases=[dict(repeat_limit=r['bytes12_15'][0],speed_source_byte=r['bytes12_15'][2],flags=r['bytes12_15'][3]) for r in a['records']])
path=Path('assets/scenes/sally-playback/controlled.json'); config=json.loads(path.read_text())
config['controls']['run']=dict(clip=template('7100B0E9'),descriptor=descriptor('71004D9E'),transitions=decoded['71004D9E']['tables'],
    stop_a=template('9E0004DD'),stop_b=template('9E0004DE'),stop_descriptor=descriptor('9E0004D5'),stop_transitions=decoded['9E0004D5']['tables'])
config['run_provenance']=dict(inputs=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths],
    selected_templates=selected_templates,
    limits='Running and both stop53 source phases qualified (213501 has30 consistent stop snapshots). Stop templates use steady observed VM speed56; the initial binding60 callback ordering is not reconstructed. Keyboard Shift/R2 selection remains preview policy. Full controller/pose parity unproven.')
path.write_text(json.dumps(config,separators=(',',':')))
print(json.dumps(dict(path=str(path),speed=config['controls']['run']['clip']['speed'])))
