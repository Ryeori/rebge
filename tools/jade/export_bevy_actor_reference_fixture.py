"""Explicit primary-reference inputs vs observed root local; no error filtering."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from jade_trace_consistency import rejection_reasons
from match_sally_runtime_clip import signature
from probe_transition_pose import channels
from project_paths import ASSET_ROOT,report_path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('sequence',type=Path);args=parser.parse_args()
    raw=args.sequence.read_bytes();record=json.loads(raw);sources={}
    for path in (ASSET_ROOT/'animations/sally/local-samples').glob('*.json'):
        clip=json.loads(path.read_text());sources.setdefault(json.dumps(signature(clip['tracks'])),[]).append((path.stem,clip))
    cases=[];skipped=[]
    for sample in record['samples']:
        if rejection_reasons(sample) or sample['component_flags_u16']>>8&15!=1:continue
        choices=sources.get(json.dumps(signature(sample['primary_clip']['tracks'],True)),[])
        if len(choices)!=1:raise ValueError('Unique source required')
        key,source=choices[0];values,missing=channels(source,sample['primary_clip']['tracks'])
        if missing or 'position_xyz' not in values.get(0,{}):
            skipped.append(sample['index']);continue
        actor_flags=int(sample['actor']['flags'],16)
        if actor_flags&0x400000:raise ValueError('Linked actor context unsupported')
        reference=struct.unpack('<16fI',bytes.fromhex(sample['actor_reference_matrix_hex']));actor=sample['actor']['world_matrix']
        cases.append(dict(sample_index=sample['index'],source_key=key,position=values[0]['position_xyz'],
                          reference=list(reference[:16]),reference_flags=reference[16],actor=actor[:16],actor_flags=int(actor[16]),
                          height=sample['component_height_b4'],add_height=bool(actor_flags&2),observed=sample['objects'][0]['linked_local_matrix'][12:15],
                          rotation=values[0]['quaternion_xyzw'],observed_matrix=sample['objects'][0]['linked_local_matrix']))
        if len(cases)==32:break
    if len(cases)!=32:raise ValueError('Insufficient qualified reference cases')
    path=report_path('stage43-bevy-actor-reference-native.json')
    path.write_text(json.dumps(dict(source_record=str(args.sequence),source_sha256=hashlib.sha256(raw).hexdigest(),cases=cases,skipped=skipped,
        limitations=['Observed reference/actor inputs are conditional, not callback-entry proven.','Stationary primary clip only; no moving/transition root parity claim.']),indent=2))
    print(json.dumps(dict(report=str(path),cases=len(cases))))


if __name__=='__main__':main()
