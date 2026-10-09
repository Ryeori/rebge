"""Qualified temporal channel comparison, excluding tracking and root writes."""
import argparse
import json
from collections import Counter
from pathlib import Path
from jade_trace_consistency import rejection_reasons
from match_sally_runtime_clip import signature
from probe_transition_pose import channels
from jade_pose import rotation_matrix
from jade_matrix_quaternion import matrix_quaternion
from jade_pose_blend import blend_rotation
from jade_animation_transition import f32
from project_paths import ASSET_ROOT,report_path
from jade_animation_sample import sample_local_track
from jade_rotation_channel import rotation_at_state
from jade_translation_channel import translation_at_state
from jade_actor_reference import actor_reference_position
import struct


def root_translation(source,states):
    """Restricted identity root-rotation cancellation hypothesis for this trace."""
    position=None;rotation=None
    for track,state in zip(source['tracks'],states):
        if track['short1']!=65535:continue
        index=state['frame_index']
        # Events do not supply transform channels; retain explicit root transforms.
        if track['frames'][index]['flags']&0x7c0!=0x80:continue
        absolute=sum(f['tick_raw']/60 for f in track['frames'][:index])+state['elapsed_seconds']
        sample=sample_local_track(track,absolute)
        q=rotation_at_state(track,state)
        if q is not None:rotation=q
        value=translation_at_state(track,state)
        if value is not None:position=value
    if position is None or rotation is None or max(abs(v) for v in rotation[:3])>1e-6:
        raise ValueError('Identity root rotation/translation unavailable')
    return position


def main():
    parser=argparse.ArgumentParser();parser.add_argument('snapshot',type=Path)
    args=parser.parse_args();sequence=json.loads(args.snapshot.read_text())
    sources={}
    for path in sorted((ASSET_ROOT/'animations/sally/local-samples').glob('*.json')):
        source=json.loads(path.read_text())
        sources.setdefault(json.dumps(signature(source['tracks'])),[]).append((path.stem,source))
    rows=[];skipped=[];clips=Counter()
    for sample in sequence['samples']:
        if rejection_reasons(sample):continue
        try:
            active=sample['component_flags_u16']>>8&15
            selected=[];roots=[]
            for name in ('primary','transition') if active==3 else ('primary',):
                tracks=sample[name+'_clip']['tracks']
                candidates=sources.get(json.dumps(signature(tracks,True)),[])
                if len(candidates)!=1:raise ValueError(name+' source ambiguous/absent')
                key,source=candidates[0];values,missing=channels(source,tracks)
                if missing:raise ValueError(name+' unsupported channel segments')
                selected.append((key,values))
                try:roots.append(root_translation(source,tracks))
                except ValueError:roots.append(None)
            clips[tuple(key for key,_ in selected)]+=1
            if active==3 and bytes.fromhex(sample['transition_header_hex'])[0x57]&128:
                raise ValueError('Transition blend suppressed; destination writes not reconstructed')
            for obj in sample['objects']:
                slot=obj['slot']
                if slot in (9,10,20) or 'linked_local_matrix' not in obj:continue
                if not all(slot in values for _,values in selected):continue
                actual=obj['linked_local_matrix'];primary=selected[0][1][slot]
                row=dict(sample=sample['index'],slot=slot,active_slots=active)
                if active==1:
                    expected_q=primary.get('quaternion_xyzw');expected_p=primary.get('position_xyz')
                else:
                    transition=selected[1][1][slot];weight=sample['transition_clip']['tracks'][0]['auxiliary_f32']
                    expected_q=None;expected_p=None
                    if all('quaternion_xyzw' in v for v in (primary,transition)):
                        operands=[matrix_quaternion(rotation_matrix(v['quaternion_xyzw']))
                                  for v in (transition,primary)]
                        expected_q=blend_rotation(*operands,weight)
                    if all('position_xyz' in v for v in (primary,transition)):
                        t=f32(max(0,min(1,weight)))
                        expected_p=[f32(f32(f32(1-t)*a)+f32(t*b)) for a,b in
                                    zip(transition['position_xyz'],primary['position_xyz'])]
                if expected_q is not None:
                    expected=rotation_matrix(expected_q)
                    row['rotation_error']=max(abs(actual[i]-expected[i]) for i in (0,1,2,4,5,6,8,9,10))
                if expected_p is not None:
                    row['position_error']=max(abs(a-b) for a,b in zip(actual[12:15],expected_p))
                    if slot==0 and all(root is not None for root in roots):
                        primary_p=[f32(a-b) for a,b in zip(primary['position_xyz'],roots[0])]
                        if active==1:corrected=primary_p
                        else:
                            transition_p=[f32(a-b) for a,b in zip(transition['position_xyz'],roots[1])]
                            corrected=[f32(f32(f32(1-t)*a)+f32(t*b)) for a,b in zip(transition_p,primary_p)]
                        row['root_cancelled_position_error']=max(abs(a-b) for a,b in zip(corrected,actual[12:15]))
                    if slot==0 and sample.get('actor_reference_matrix_hex') and sample.get('actor_reference_unchanged'):
                        ref=struct.unpack('<16fI',bytes.fromhex(sample['actor_reference_matrix_hex']))
                        actor=sample['actor']['world_matrix'];actor_flags=int(sample['actor']['flags'],16)
                        if actor_flags&0x400000:raise ValueError('Linked actor local reference input not captured')
                        convert=lambda p:actor_reference_position(p,ref[:16],ref[16],actor[:16],int(actor[16]),
                            height=sample['component_height_b4'],add_height=bool(actor_flags&2))
                        primary_ref=convert(primary['position_xyz'])
                        if active==1:corrected=primary_ref
                        else:
                            transition_ref=convert(transition['position_xyz'])
                            corrected=[f32(f32(f32(1-t)*a)+f32(t*b)) for a,b in zip(transition_ref,primary_ref)]
                        row['actor_reference_position_error']=max(abs(a-b) for a,b in zip(corrected,actual[12:15]))
                        if active==3:
                            # 1409bbd60 selects transition instance+0x10, not actor accessor.
                            transition_matrix=struct.unpack('<16fI',bytes.fromhex(sample['transition_header_hex'])[16:84])
                            if transition_matrix[16]&6==6 and not transition_matrix[16]&8:
                                transition_ref=actor_reference_position(transition['position_xyz'],
                                    transition_matrix[:16],transition_matrix[16],actor[:16],int(actor[16]),
                                    height=sample['component_height_b4'],add_height=bool(actor_flags&2))
                                corrected=[f32(f32(f32(1-t)*a)+f32(t*b)) for a,b in zip(transition_ref,primary_ref)]
                                row['transition_instance_reference_position_error']=max(abs(a-b) for a,b in zip(corrected,actual[12:15]))
                rows.append(row)
        except (ValueError,NotImplementedError) as error:
            skipped.append(dict(sample=sample['index'],reason=str(error)))
    result=dict(snapshot=str(args.snapshot),skipped=skipped,rows=rows,
        clip_combinations=[dict(keys=list(keys),samples=count) for keys,count in clips.items()],
        limitations=['Qualified reads are consistency evidence, not atomic callback inputs.',
                    'Root/tracking excluded; reference conversion, missing prior channels and scales not reconstructed.',
                    'Source channel interpolation remains numerical; no final native pose parity claim.'])
    for active in (1,3):
        subset=[r for r in rows if r['active_slots']==active]
        result['primary_only' if active==1 else 'transition_active']={
            field:dict(checked=sum(field+'_error' in r for r in subset),
                       matched=sum(r.get(field+'_error',1)<=1e-5 for r in subset),
                       maximum_error=max((r[field+'_error'] for r in subset if field+'_error' in r),default=None))
            for field in ('rotation','position')}
    ordinary_positions=[r['position_error'] for r in rows if r['slot']!=0 and 'position_error' in r]
    result['positions_excluding_slot0']=dict(checked=len(ordinary_positions),
        matched=sum(error<=1e-5 for error in ordinary_positions),
        maximum_error=max(ordinary_positions,default=None))
    result['position_failure_slots']=dict(Counter(r['slot'] for r in rows if r.get('position_error',0)>1e-5))
    cancelled=[r['root_cancelled_position_error'] for r in rows if 'root_cancelled_position_error' in r]
    result['slot0_identity_root_cancellation']=dict(checked=len(cancelled),
        matched=sum(e<=1e-5 for e in cancelled),maximum_error=max(cancelled,default=None),
        limitation='Restricted identity-root subtraction diagnostic; does not apply full reference conversion.')
    referenced=[r['actor_reference_position_error'] for r in rows if 'actor_reference_position_error' in r]
    result['slot0_actor_reference']=dict(checked=len(referenced),matched=sum(e<=1e-5 for e in referenced),
        maximum_error=max(referenced,default=None),
        limitation='Active transition reference selection is conditional; primary actor accessor route only.')
    result['slot0_actor_reference_by_active_slots']={str(active):dict(checked=len(errors),
        matched=sum(e<=1e-5 for e in errors),maximum_error=max(errors,default=None))
        for active in (1,3) for errors in [[r['actor_reference_position_error'] for r in rows
            if r['active_slots']==active and 'actor_reference_position_error' in r]]}
    errors=[r['transition_instance_reference_position_error'] for r in rows if 'transition_instance_reference_position_error' in r]
    result['slot0_transition_instance_reference']=dict(checked=len(errors),matched=sum(e<=1e-5 for e in errors),
        maximum_error=max(errors,default=None),limitation='Transition instance reference observed after update; callback input timing not proven.')
    report_path(args.snapshot.stem+'-motion-pose.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','skipped')}))
    print('skipped_samples',len(skipped))


if __name__=='__main__':main()
