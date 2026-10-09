"""Fixed actor/root diagnostic: original geometry + ordinary source clip playback.
No controller, transitions, moving tracking or contacts are inferred here.
"""
import json,hashlib,struct,collections
from pathlib import Path
from project_paths import ASSET_ROOT,report_path
from jade_trace_consistency import rejection_reasons
from match_sally_runtime_clip import signature
from jade_target_hierarchy import snapshot_target_nodes

def main():
    scene_path=ASSET_ROOT/'scenes/sally-runtime-skin/scene.json'
    scene=json.loads(scene_path.read_text())
    seed_path=report_path('stage4-sally-runtime-20261008-172956-runtime-palette.json')
    seed=json.loads(seed_path.read_text())
    sequence_path=report_path('stage43-tracking-sequence-20261008-182519.json')
    sequence=json.loads(sequence_path.read_text())
    sample=next(s for s in sequence['samples'] if not rejection_reasons(s))
    key='7100B1C3'
    clip=json.loads((ASSET_ROOT/f'animations/sally/local-samples/{key}.json').read_text())
    rig=json.loads((ASSET_ROOT/'skeletons/sally/gao-parent-links.json').read_text())
    binding=json.loads((ASSET_ROOT/'skeletons/sally/animation-binding.json').read_text())
    tracks=[]
    for native,source in zip(sample['primary_clip']['tracks'],clip['tracks']):
        assert native['indexed_slot']==source['short1']
        assert [(f['tick_raw'],f['flags']&~4) for f in native['frame_headers']]==[(f['tick_raw'],f['flags']&~4) for f in source['frames']]
        if native['indexed_slot'] in (65535,0):continue
        if any(f['flags']!=128 for f in native['frame_headers']):raise ValueError('Unsupported ordinary callback keys')
        tracks.append(dict(index=native['track_index'],clock=dict(frames=native['frame_headers'],flags=native['track_flags'],auxiliary_short=native['auxiliary_short_u16']),
            state=dict(index=native['frame_index'],elapsed=native['elapsed_seconds'],flags=native['state_flags'])))
    dependencies=json.loads(report_path('stage4-sally-variant-dependencies.json').read_text())
    variants=json.loads(report_path('stage4-sally-variant-geometry.json').read_text())
    objects={o['key']:o for o in variants['objects']};skins={s['gao']:s for s in dependencies['skins']}
    fixture=[]
    for batch in scene['batches']:
        mesh=json.loads((ASSET_ROOT/f"models/meshes/sally-{batch['mesh']}.json").read_text())
        skin=skins.get(batch['object']); ext=mesh['extended_header'];records=[]
        if ext and skin:
            mirror=not bool(objects[batch['object']]['gao'].get('visual_flags',0)&0x8000)
            records=[dict(palette_index=skin['bindings'][r['index_u16']]['matrix_index'],bind=r['matrix'],bind_flags=r['matrix_flags'],words=r['words_u32'],mirror=mirror) for r in ext['records']]
            rigid=None
        else:
            rigid=next(l['slot'] for l in variants['links'] if l['gao']==batch['object'])
        sub=next(s for s in mesh['submeshes'] if s['unknown']==batch['selector'])
        indices=[i for tri in sub['triangles'] for i in tri[:3]]
        deformation=dict(positions=mesh['positions'],records=records,vertex_indices=indices,rigid_slot=rigid)
        assert len(indices)*5==len(batch['vertices'])
        fixture.append(dict(deformation=deformation,expected=[batch['vertices'][i:i+3] for i in range(0,len(batch['vertices']),5)]))
        batch['deformation']=deformation
        if batch['mesh']=='6200318D' and batch['selector'] in (2,3):
            child=dependencies['materials'][batch['material']]['materials'][batch['selector']]
            layer=dependencies['materials'][child]['layers'][0]
            _,descriptor,flags,packed_u,packed_v,_=struct.unpack('<HHIIII',bytes.fromhex(layer['source_hex']))
            batch['uv_projection']=dict(descriptor=descriptor,flags=flags,packed_u=packed_u,packed_v=packed_v)
    oracle_snapshot=Path(scene['runtime_snapshot'])
    palette=json.loads(oracle_snapshot.read_text())['palette']['matrices']
    report_path('stage43-cpu-skin-python-oracle.json').write_text(json.dumps(dict(cases=fixture,palette=palette,
        source_scene_sha256=hashlib.sha256(scene_path.read_bytes()).hexdigest(),source_snapshot=str(oracle_snapshot),source_snapshot_sha256=hashlib.sha256(oracle_snapshot.read_bytes()).hexdigest(),limitations=['Python numerical oracle, not native GPU vertex capture.'])))
    seed_objects={o['slot']:o for o in json.loads(Path(seed['source_snapshot']).read_text())['objects']}
    records=[dict(bone=p['bone'],state_hex=p['state_hex'],record_flags=seed_objects[p['slot']]['modifier24_records'][0]['record_flags']) for p in seed['modifier_publications']]
    limits='Diagnostic ordinary walking playback. Actor/root fixed from native seed; no controller, transitions, moving tracking, contacts or native rendered-frame parity.'
    config=dict(rig=rig,binding=binding,clip=clip,tracks=tracks,nodes=seed['nodes'],bone_addresses=seed['bone_addresses'],actor_address=seed['actor_address'],
        modifiers=records,modifier_requests=[28],speed=bytes.fromhex(sample['primary_header_hex'])[2],palette_bones=[next(i for i,b in enumerate(rig['objects']) if b['slot']==slot) for slot in range(47)],
        source_seed=str(seed_path),source_seed_sha256=hashlib.sha256(seed_path.read_bytes()).hexdigest(),source_sequence=str(sequence_path),source_sequence_sha256=hashlib.sha256(sequence_path.read_bytes()).hexdigest(),clip_key=key,limits=limits)
    output=ASSET_ROOT/'scenes/sally-playback';output.mkdir(parents=True,exist_ok=True)
    (output/'animation.json').write_text(json.dumps(config))
    scene.update(name='Sally ordinary walking playback · fixed root diagnostic',animation='scenes/sally-playback/animation.json',limits=limits)
    (output/'scene.json').write_text(json.dumps(scene))
    transition_source=report_path('stage43-tracking-sequence-20261008-183132.json')
    outgoing_key='7100B5E3'
    outgoing_clip=json.loads((ASSET_ROOT/f'animations/sally/local-samples/{outgoing_key}.json').read_text())
    transition_sample=next(s for s in json.loads(transition_source.read_text())['samples']
        if not rejection_reasons(s) and s['component_flags_u16']>>8&15==3
        and signature(s['primary_clip']['tracks'],True)==signature(clip['tracks'])
        and signature(s['transition_clip']['tracks'],True)==signature(outgoing_clip['tracks']))
    def track_inputs(name):
        values=[]
        for t in transition_sample[name+'_clip']['tracks']:
            if t['indexed_slot'] in (65535,0):continue
            if any(f['flags']!=128 for f in t['frame_headers']):raise ValueError('Unsupported transition callback track')
            values.append(dict(index=t['track_index'],clock=dict(frames=t['frame_headers'],flags=t['track_flags'],auxiliary_short=t['auxiliary_short_u16']),
                state=dict(index=t['frame_index'],elapsed=t['elapsed_seconds'],flags=t['state_flags'])))
        return values
    header=bytes.fromhex(transition_sample['transition_header_hex'])
    config['tracks']=track_inputs('primary')
    config['speed']=bytes.fromhex(transition_sample['primary_header_hex'])[2]
    config['transition']=dict(clip=outgoing_clip,tracks=track_inputs('transition'),speed=header[2],duration_byte=header[0x59],elapsed_u16=struct.unpack_from('<H',header,0x5a)[0],
        ratio=transition_sample['transition_clip']['tracks'][0]['auxiliary_f32'],active=True)
    config['transition_provenance']=dict(source=str(transition_source),sha256=hashlib.sha256(transition_source.read_bytes()).hexdigest(),sample=transition_sample['index'],outgoing_key=outgoing_key,primary_key=key)
    config['limits']=limits+' One native-seeded outgoing-to-primary transition; full controller and reference-root blend excluded.'
    (output/'transition.json').write_text(json.dumps(config))
    scene.update(name='Sally two-clip transition · fixed root diagnostic',animation='scenes/sally-playback/transition.json',limits=config['limits'])
    (output/'transition-scene.json').write_text(json.dumps(scene))
    def root_inputs(name,reference):
        tracks=[]
        for t in transition_sample[name+'_clip']['tracks']:
            if t['indexed_slot']!=0:continue
            tracks.append(dict(index=t['track_index'],clock=dict(frames=t['frame_headers'],flags=t['track_flags'],auxiliary_short=t['auxiliary_short_u16']),state=dict(index=t['frame_index'],elapsed=t['elapsed_seconds'],flags=t['state_flags'])))
        return dict(tracks=tracks,reference=list(reference[:16]),reference_flags=reference[16],height=transition_sample['component_height_b4'],add_height=bool(int(transition_sample['actor']['flags'],16)&2))
    native_objects={o['slot']:o for o in transition_sample['objects']}
    config['actor_address']=int(transition_sample['actor']['address'],16)
    config['bone_addresses']=[int(native_objects[b['slot']]['address'],16) if b['slot'] is not None else config['actor_address'] for b in rig['objects']]
    config['nodes']=[dict(address=a,flags=n['flags'],world=n['world_matrix'],world_flags=n['world_flags'],parent=n.get('parent_address'),local=n.get('local_matrix'),local_flags=n.get('local_flags')) for a,n in snapshot_target_nodes(transition_sample).items()]
    config['modifiers']=[dict(bone=next(i for i,b in enumerate(rig['objects']) if b['slot']==slot),state_hex=native_objects[slot]['modifier24_records'][0]['state_hex'],record_flags=native_objects[slot]['modifier24_records'][0]['record_flags']) for slot in (27,28)]
    config['root']=root_inputs('primary',struct.unpack('<16fI',bytes.fromhex(transition_sample['actor_reference_matrix_hex'])))
    config['transition']['root']=root_inputs('transition',struct.unpack('<16fI',header[16:84]))
    config['actor_motion']=dict(tracks=[dict(index=t['track_index'],clock=dict(frames=t['frame_headers'],flags=t['track_flags'],auxiliary_short=t['auxiliary_short_u16']),state=dict(index=t['frame_index'],elapsed=t['elapsed_seconds'],flags=t['state_flags'])) for t in transition_sample['primary_clip']['tracks'] if t['indexed_slot']==65535 and t['track_flags']&0x8000],entry_gate=1,dispatch_flags=0)
    config['excluded_actor_event_tracks']=[t['track_index'] for t in transition_sample['primary_clip']['tracks'] if t['indexed_slot']==65535 and not t['track_flags']&0x8000]
    config['limits']='Source-driven root motion with reference-converted two-clip slot0 blend. Explicit diagnostic publication policy; no VM actor setters, collision, moving tracking or controller phase changes. Primary actor motion only, outgoing actor motion excluded.'
    (output/'root-motion.json').write_text(json.dumps(config))
    scene.update(name='Sally root motion and transition · diagnostic',animation='scenes/sally-playback/root-motion.json',root_motion=True,limits=config['limits'])
    (output/'root-motion-scene.json').write_text(json.dumps(scene))
    all_samples=json.loads(transition_source.read_text())['samples']
    initial_sequence=report_path('stage43-tracking-sequence-20261009-150304.json')
    initial_samples=json.loads(initial_sequence.read_text())['samples']
    def template(key, samples=None):
        samples=all_samples if samples is None else samples
        clip=json.loads((ASSET_ROOT/f'animations/sally/local-samples/{key}.json').read_text())
        matches=[s for s in samples if not rejection_reasons(s) and signature(s['primary_clip']['tracks'],True)==signature(clip['tracks'])]
        if not matches:raise ValueError('No qualified primary template for '+key)
        sample=matches[0]
        speed=collections.Counter(bytes.fromhex(s['primary_header_hex'])[2] for s in matches).most_common(1)[0][0]
        tracks=[];roots=[];actors=[];excluded=[]
        for t in sample['primary_clip']['tracks']:
            row=dict(index=t['track_index'],clock=dict(frames=t['frame_headers'],flags=t['track_flags'],auxiliary_short=t['auxiliary_short_u16']),state=dict(index=0,elapsed=0.,flags=5 if t['indexed_slot']==65535 else 1))
            if t['indexed_slot']==65535:
                if t['track_flags']&0x8000:actors.append(row)
                else:excluded.append(t['track_index'])
            elif t['indexed_slot']==0:roots.append(row)
            else:tracks.append(row)
        return dict(key=key,clip=clip,tracks=tracks,root_tracks=roots,actor_tracks=actors,speed=speed,source_sample=sample['index'],excluded_event_tracks=excluded)
    config['controls']=dict(idle=template('7100B0E7'),start=template('7100B5E3'),walk=template('7100B1C3'),stop_a=template('7100B5A4'),stop_b=template('7100B5B0'),transition_duration_byte=8)
    config['controls']['waiting_idle']=template('2600313F',initial_samples)
    config['controls']['slow']=template('7100B0E8',initial_samples)
    restart_sequence=report_path('stage43-tracking-sequence-20261009-152034.json')
    config['controls']['restart']=template('7100B2E4',json.loads(restart_sequence.read_text())['samples'])
    config['restart_clip_provenance']=dict(source=str(restart_sequence),sha256=hashlib.sha256(restart_sequence.read_bytes()).hexdigest())
    config['initial_clip_provenance']=dict(source=str(initial_sequence),sha256=hashlib.sha256(initial_sequence.read_bytes()).hexdigest())
    actions_path=report_path('stage4-sally-actions.json')
    actions=json.loads(actions_path.read_text())['actions']
    def descriptor(key):
        action=next(a for a in actions if a['key']==key)
        return dict(loop_phase=action['header_byte1'],phases=[dict(repeat_limit=r['bytes12_15'][0],speed_source_byte=r['bytes12_15'][2],flags=r['bytes12_15'][3]) for r in action['records']])
    selector_path=report_path('stage43-tracking-sequence-20261009-145240.json')
    selector_sample=json.loads(selector_path.read_text())['samples'][0]
    config['controls']['selector_actions']=selector_sample['selector_inputs']['actions_04_30']
    config['selector_provenance']=dict(source=str(selector_path),sha256=hashlib.sha256(selector_path.read_bytes()).hexdigest(),sample=0)
    config['controls']['walk_descriptor']=descriptor('71005EAC')
    config['controls']['stop_descriptor']=descriptor('7100B466')
    config['controls']['idle_descriptor']=descriptor('71004D9C')
    transitions_path=report_path('stage43-action-transition-decoded-20261009.json')
    transitions=json.loads(transitions_path.read_text())['actions']
    config['controls']['start_transitions']=transitions['7100B730']['tables']
    config['controls']['walk_transitions']=transitions['71005EAC']['tables']
    config['controls']['idle_transitions']=transitions['71004D9C']['tables']
    config['controls']['slow_transitions']=transitions['71004D9D']['tables']
    config['controls']['restart_transitions']=transitions['9E0004D3']['tables']
    config['controls']['stop_transitions']=transitions['7100B466']['tables']
    config['controls']['waiting_transitions']=transitions['26003175']['tables']
    stationary_source=report_path('stage43-tracking-sequence-20261009-152531.json')
    stationary_sample=json.loads(stationary_source.read_text())['samples'][57]
    stationary=stationary_sample['stationary_selector_inputs']
    f32=lambda data:struct.unpack('<f',bytes.fromhex(data))[0]
    config['controls']['stationary_context']=dict(
        scene_time=f32(stationary['globals_hex']['0x1420a3310']),
        time_origin=f32(stationary['globals_hex']['0x14210c174']),
        interaction_time=f32(stationary['brain_hex']['0xdac']),
        mode=stationary['mode_34'],pending=stationary['pending_44'],
        selected_action=stationary['selected_action_1124'])
    config['stationary_provenance']=dict(source=str(stationary_source),sha256=hashlib.sha256(stationary_source.read_bytes()).hexdigest(),sample=57,limits='Frozen normal-mode interaction context; no interaction writers or native wall-clock synchronization.')
    config['transition_provenance']=dict(source=str(transitions_path),sha256=hashlib.sha256(transitions_path.read_bytes()).hexdigest())
    config['action_descriptor_provenance']=dict(source=str(actions_path),sha256=hashlib.sha256(actions_path.read_bytes()).hexdigest())
    config['limits']='Diagnostic W input: qualified waiting123/slow1/start4/walk3 and idle0/intermediary51/start4/walk3 paths. Stop re-entry uses scalar, blend gate and phase tables. Incoming self rows restart; flags1 transfers progress. Intermediary51 phase1 has no qualified template and errors if reached. Source descriptors control repeats, stop carry and queued idle. Stationary idle0 selects waiting123 after2s using frozen native interaction context. Target1 and normal mode remain diagnostic. Input dispatch timing, interaction writers, idle timestamp writer timing, native seek input timing, direction, collisions and moving tracking remain provisional or excluded.'
    (output/'controlled.json').write_text(json.dumps(config))
    scene.update(name='Sally W start-stop · provisional control diagnostic',animation='scenes/sally-playback/controlled.json',locomotion_controls=True,limits=config['limits'])
    (output/'controlled-scene.json').write_text(json.dumps(scene))
    closeup=dict(scene,root_motion=False,preview_camera=dict(target=[0.,1.43,0.],distance=.55,yaw=-2.34,pitch=0.))
    (output/'eye-closeup-scene.json').write_text(json.dumps(closeup))
    print(json.dumps(dict(scene=str(output/'scene.json'),tracks=len(tracks),batches=len(scene['batches']),limits=limits)))

if __name__=='__main__':main()
