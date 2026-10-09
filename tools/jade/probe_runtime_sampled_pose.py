"""Saved-state ordinary channel oracle, excluding root and full pose assembly."""
import json
import argparse
from pathlib import Path
from copy import deepcopy
from jade_animation import packed_quaternion_float32
from jade_animation_sample import sample_local_track
from jade_animation_root import rigid_inverse
from jade_pose import affine_product, rotation_matrix
from jade_basis_normalize import normalize_basis
from project_paths import ASSET_ROOT, report_path
from match_sally_runtime_clip import signature


def select_runtime_tracks(snapshot, source, instance):
    native = snapshot['animation_state']['instances'][instance]['clip_link']['tracks']
    if signature(source['tracks']) != signature(native, True):
        raise ValueError('Source frame headers do not match selected runtime instance')
    return native


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--snapshot',type=Path,default=report_path('stage4-sally-runtime-20261008-145025.json'))
    parser.add_argument('--key',default='26000546')
    parser.add_argument('--instance',choices=('primary','transition'),default='primary')
    args=parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text())
    source = deepcopy(json.loads((ASSET_ROOT/'animations/sally/local-samples'/f'{args.key}.json').read_text()))
    links = json.loads(report_path('stage4-sally-transform-links.json').read_text())
    objects = sorted((obj for obj in links['objects'] if obj.get('slot') is not None),key=lambda obj:obj['slot'])
    slots = {obj['key']:obj['slot'] for obj in objects}
    native = select_runtime_tracks(snapshot, source, args.instance)
    rows, skipped = [], []
    for track,state in zip(source['tracks'],native):
        try:
            slot=track['short1']
            if slot==65535:
                raise ValueError('Actor root needs captured reference context')
            if not 0<=slot<len(objects):
                raise ValueError('Invalid indexed slot')
            for frame in track['frames']:
                transform=frame.get('transform',{})
                if 'packed_rotation' in transform:
                    transform['quaternion_xyzw']=packed_quaternion_float32(transform['packed_rotation'])
            index=state['frame_index']
            if index>=len(track['frames']):
                raise ValueError('Native frame index outside source')
            absolute=sum(frame['tick_raw']/60 for frame in track['frames'][:index])+state['elapsed_seconds']
            sample=sample_local_track(track,absolute)
            if sample['frame_index']!=index:
                raise ValueError('Reconstructed segment disagrees with native state')
            obj=objects[slot]
            parent_slot=slots.get(obj.get('linked_gao'))
            parent=(snapshot['actor']['world_matrix'][:16] if parent_slot is None else
                    snapshot['objects'][parent_slot]['matrix'])
            local=affine_product(snapshot['objects'][slot]['matrix'],rigid_inverse(parent))
            palette_parent=(rotation_matrix([0,0,0,1]) if parent_slot is None else
                            snapshot['palette']['matrices'][parent_slot]['matrix'])
            palette_local=affine_product(snapshot['palette']['matrices'][slot]['matrix'],
                                        rigid_inverse(palette_parent))
            row={'track_index':track['index'],'slot':slot,'frame_index':index,
                 'segment_seconds':state['elapsed_seconds']}
            if 'quaternion_xyzw' in sample:
                expected=rotation_matrix(sample['quaternion_xyzw'])
                row['rotation_basis_max_error']=max(abs(expected[i]-local[i]) for i in (0,1,2,4,5,6,8,9,10))
                row['palette_rotation_basis_max_error']=max(abs(expected[i]-palette_local[i]) for i in (0,1,2,4,5,6,8,9,10))
                captured_local=snapshot['objects'][slot].get('linked_local_matrix')
                if captured_local is not None:
                    row['actual_local_rotation_error']=max(abs(expected[i]-captured_local[i]) for i in (0,1,2,4,5,6,8,9,10))
                    normalized=normalize_basis(expected)
                    row['normalized_expected_local_rotation_error']=max(abs(normalized[i]-captured_local[i]) for i in (0,1,2,4,5,6,8,9,10))
                    row['actual_parent_address']=snapshot['objects'][slot].get('linked_parent_address')
                    row['source_parent_runtime_address']=(snapshot['actor']['address'] if parent_slot is None else
                                                         snapshot['objects'][parent_slot]['address'])
            if 'position_xyz' in sample:
                row['position_max_error']=max(abs(a-b) for a,b in zip(sample['position_xyz'],local[12:15]))
            rows.append(row)
        except ValueError as error:
            skipped.append({'track_index':track['index'],'reason':str(error)})
    result={'snapshot':str(args.snapshot),'resource_key':args.key,'instance':args.instance,'checked_tracks':len(rows),'skipped_tracks':skipped,'tracks':rows,
            'rotation_tracks_within_1e_5':sum(r.get('rotation_basis_max_error',float('inf'))<=1e-5 for r in rows),
            'position_tracks_within_1e_5':sum(r.get('position_max_error',float('inf'))<=1e-5 for r in rows),
            'max_rotation_error':max((r.get('rotation_basis_max_error',0) for r in rows),default=None),
            'max_position_error':max((r.get('position_max_error',0) for r in rows),default=None),
            'limits':'Source parent graph, rigid inverse and unsynchronised live world matrices. '
                     'Expected local basis normalization compared separately; full native '
                     'matrix/scale pipeline and active transition effects not reproduced. '
                     'No full pose parity claim.'}
    report_path('stage43-runtime-sampled-pose.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='tracks'}))


if __name__=='__main__':main()
