"""Recorded final locals/actor/native palette, fixed modifier24 exclusions."""
import argparse
import hashlib
import json
from pathlib import Path
from jade_target_hierarchy import snapshot_target_nodes
from project_paths import ASSET_ROOT


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('snapshot',type=Path)
    args=parser.parse_args()
    raw=args.snapshot.read_bytes();snapshot=json.loads(raw)
    actor=int(snapshot['actor']['address'],16)
    rig_path=ASSET_ROOT/'skeletons/sally/gao-parent-links.json'
    rig_raw=rig_path.read_bytes();rig=json.loads(rig_raw)
    objects={obj['slot']:obj for obj in snapshot['objects']}
    addresses=[int(objects[bone['slot']]['address'],16) if bone['slot'] is not None else actor
               for bone in rig['objects']]
    if len(set(addresses))!=len(addresses):raise ValueError('Unique runtime mapping required')
    nodes=snapshot_target_nodes(snapshot)
    serialized=[dict(address=a,flags=n['flags'],world=n['world_matrix'],world_flags=n['world_flags'],
        parent=n.get('parent_address'),local=n.get('local_matrix'),local_flags=n.get('local_flags'))
        for a,n in nodes.items()]
    bone_indices={bone['slot']:index for index,bone in enumerate(rig['objects']) if bone['slot'] is not None}
    excluded=[27,28]
    expected=[dict(bone=bone_indices[p['slot']],slot=p['slot'],matrix=p['matrix'],flags=p['flags'])
              for p in snapshot['palette']['matrices'] if p['slot'] not in excluded]
    expected_all=[dict(bone=bone_indices[p['slot']],slot=p['slot'],matrix=p['matrix'],flags=p['flags'])
                  for p in snapshot['palette']['matrices']]
    publications=[]
    for slot in excluded:
        obj=objects[slot]
        records=obj.get('modifier24_records',[])
        if len(records)!=1:raise ValueError('One explicit modifier24 state required')
        publications.append(dict(bone=bone_indices[slot],slot=slot,state_hex=records[0]['state_hex'],
            world=obj['matrix'],world_flags=obj['matrix_flags']))
    result=dict(source_snapshot=str(args.snapshot),source_sha256=hashlib.sha256(raw).hexdigest(),
        source_rig=str(rig_path),source_rig_sha256=hashlib.sha256(rig_raw).hexdigest(),
        actor_address=actor,gao_flags=int(snapshot['actor']['flags'],16),
        actor=snapshot['actor']['world_matrix'],bone_addresses=addresses,nodes=serialized,
        expected=expected,expected_all=expected_all,modifier_publications=publications,
        excluded_slots=excluded,pose_consistency=snapshot['pose_consistency'],
        limitations=['Observed final locals include animation/blend/procedural results; no source-only playback claim.',
                     'Modifier24 slots27/28 require their separate world finalize stage and are excluded by category.',
                     'Sequential native snapshot, not atomic callback inputs or frame replay.'])
    result['limitations'].append('Modifier finalizer numerical replay uses already finalized states; actual processed-list membership was not captured.')
    path=args.snapshot.with_name(args.snapshot.stem+'-runtime-palette.json')
    path.write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(report=str(path),bones=len(addresses),expected=len(expected),excluded=excluded)))


if __name__=='__main__':main()
