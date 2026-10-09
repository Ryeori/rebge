"""Observed local/world consistency fixture, excluding known modifier24 slots.

Recorded locals are explicit inputs, not reconstructed ordinary animation.
This does not prove callback timing or source animation -> rendered world parity.
"""
import argparse
import hashlib
import json
from pathlib import Path
from jade_target_hierarchy import snapshot_target_nodes
from jade_trace_consistency import rejection_reasons
from project_paths import report_path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('sequence',type=Path)
    args=parser.parse_args();raw=args.sequence.read_bytes();record=json.loads(raw)
    cases=[]
    for sample in record['samples']:
        if rejection_reasons(sample):continue
        nodes=snapshot_target_nodes(sample)
        serialized=[dict(address=address,flags=node['flags'],world=node['world_matrix'],world_flags=node['world_flags'],
                         parent=node.get('parent_address'),local=node.get('local_matrix'),local_flags=node.get('local_flags'))
                    for address,node in nodes.items()]
        expected=[dict(address=int(obj['address'],16),slot=obj['slot'],world=obj['matrix'])
                  for obj in sample['objects'] if 'matrix' in obj and obj['slot'] not in (27,28)]
        cases.append(dict(sample_index=sample['index'],nodes=serialized,expected=expected))
        if len(cases)==8:break
    if not cases:raise ValueError('No qualified poses')
    result=dict(source_record=str(args.sequence),source_sha256=hashlib.sha256(raw).hexdigest(),
                excluded_slots=[27,28],exclusion_reason='Known modifier24 pre/local/world/finalize stage is separate.',
                cases=cases,limitations=['Observed final locals, not source-only ordinary channels.',
                                        'World consistency only, no callback-entry or autonomous playback proof.'])
    path=report_path('stage43-bevy-world-hierarchy-native.json');path.write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(report=str(path),samples=len(cases),comparisons=sum(len(x['expected']) for x in cases))))


if __name__=='__main__':main()
