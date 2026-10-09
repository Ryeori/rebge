"""Two captured clip channel blend; incomplete channels are never seeded from output."""
import argparse
import json
from copy import deepcopy
from pathlib import Path
from jade_animation import packed_quaternion_float32
from jade_animation_sample import sample_local_track
from jade_matrix_quaternion import matrix_quaternion
from jade_pose_blend import blend_rotation
from jade_pose import rotation_matrix
from jade_animation_transition import f32
from jade_rotation_channel import rotation_at_state
from jade_translation_channel import translation_at_state
from match_sally_runtime_clip import signature
from project_paths import ASSET_ROOT,report_path


def channels(source, states):
    values={}; skipped=[]
    for track,state in zip(deepcopy(source['tracks']),states):
        slot=track['short1']
        if slot==65535:continue
        try:
            for frame in track['frames']:
                transform=frame.get('transform',{})
                if 'packed_rotation' in transform:
                    transform['quaternion_xyzw']=packed_quaternion_float32(transform['packed_rotation'])
            index=state['frame_index']
            if not 0<=index<len(track['frames']):raise ValueError('Frame index outside source')
            absolute=sum(f['tick_raw']/60 for f in track['frames'][:index])+state['elapsed_seconds']
            sample=sample_local_track(track,absolute)
            if sample['frame_index']!=index:raise ValueError('Segment mismatch')
            rotation=rotation_at_state(track,state)
            if rotation is not None:sample['quaternion_xyzw']=rotation
            position=translation_at_state(track,state)
            if position is not None:sample['position_xyz']=position
            values.setdefault(slot,{}).update({k:v for k,v in sample.items()
                if k in ('quaternion_xyzw','position_xyz')})
        except ValueError as error:
            skipped.append(dict(slot=slot,reason=str(error)))
    return values,skipped


def main():
    parser=argparse.ArgumentParser();parser.add_argument('snapshot',type=Path)
    args=parser.parse_args();snapshot=json.loads(args.snapshot.read_text())
    sources=[(p.stem,json.loads(p.read_text())) for p in
             sorted((ASSET_ROOT/'animations/sally/local-samples').glob('*.json'))]
    animation=snapshot['animation_state'];instances=animation['instances']
    if animation['component_flags_u16']>>8&15 != 3:
        raise ValueError('Only active primary+transition slots supported')
    selected={};values={};skipped={}
    for name in ('primary','transition'):
        tracks=instances[name]['clip_link']['tracks']
        candidates=[(key,src) for key,src in sources if signature(src['tracks'])==signature(tracks,True)]
        if len(candidates)!=1:raise ValueError('Unique source match required')
        selected[name]=candidates[0][0]
        values[name],skipped[name]=channels(candidates[0][1],tracks)
    raw=bytes.fromhex(instances['transition']['raw_header_hex'])
    if raw[0x57]&128:raise ValueError('Transition blend suppressed by instance57')
    weight=instances['transition']['clip_link']['tracks'][0]['auxiliary_f32']
    rows=[]
    for slot in sorted(set(values['primary'])&set(values['transition'])):
        primary=values['primary'][slot];transition=values['transition'][slot]
        actual=snapshot['objects'][slot].get('linked_local_matrix')
        if actual is None:continue
        row=dict(slot=slot)
        if all('quaternion_xyzw' in v for v in (primary,transition)):
            # Native first operand is current transition-local, second saved primary.
            operands=[matrix_quaternion(rotation_matrix(v['quaternion_xyzw']))
                      for v in (transition,primary)]
            expected=rotation_matrix(blend_rotation(*operands,weight))
            row['rotation_error']=max(abs(actual[i]-expected[i]) for i in (0,1,2,4,5,6,8,9,10))
        if all('position_xyz' in v for v in (primary,transition)):
            t=f32(max(0,min(1,weight)));inverse=f32(1-t)
            expected=[f32(f32(inverse*a)+f32(t*b)) for a,b in
                      zip(transition['position_xyz'],primary['position_xyz'])]
            row['position_error']=max(abs(a-b) for a,b in zip(expected,actual[12:15]))
        rows.append(row)
    result=dict(snapshot=str(args.snapshot),sources=selected,weight=weight,tracks=rows,skipped=skipped,
        rotations_checked=sum('rotation_error' in r for r in rows),
        positions_checked=sum('position_error' in r for r in rows),
        rotations_matched=sum(r.get('rotation_error',1)<=1e-5 for r in rows),
        positions_matched=sum(r.get('position_error',1)<=1e-5 for r in rows),
        limitations=['Only slots with channels in both clips checked; absent writes require prior pose.',
                    'Saved reads are unsynchronised; tracking correction and root omitted.',
                    'Channel interpolation and trig remain numerical, not native bit-exact.'])
    output=report_path(args.snapshot.stem+'-transition-pose.json')
    output.write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in result.items() if k not in ('tracks','skipped')}))


if __name__=='__main__':main()
