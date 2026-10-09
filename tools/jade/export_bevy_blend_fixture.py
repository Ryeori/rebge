"""Private measured pose fixture; source operands reconstructed from channels."""
import argparse
import hashlib
import json
from pathlib import Path
from jade_modifier24 import _quaternion_matrix
from jade_trace_consistency import rejection_reasons
from match_sally_runtime_clip import signature
from probe_transition_pose import channels
from project_paths import ASSET_ROOT,report_path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('snapshot',type=Path)
    args=parser.parse_args();samples=json.loads(args.snapshot.read_text())['samples'];sources={}
    for path in (ASSET_ROOT/'animations/sally/local-samples').glob('*.json'):
        source=json.loads(path.read_text())
        sources.setdefault(json.dumps(signature(source['tracks'])),[]).append((path.stem,source))
    rows=[];provenance=[]
    for sample in samples:
        if rejection_reasons(sample) or sample['component_flags_u16']>>8&15!=3:continue
        if bytes.fromhex(sample['transition_header_hex'])[0x57]&128:continue
        operands=[];keys=[]
        for name in ('transition','primary'):
            candidates=sources.get(json.dumps(signature(sample[name+'_clip']['tracks'],True)),[])
            if len(candidates)!=1:raise ValueError('Unique source match required')
            key,source=candidates[0];values,missing=channels(source,sample[name+'_clip']['tracks'])
            if missing:raise ValueError('Unsupported source channel')
            operands.append(values);keys.append(key)
        weight=sample['transition_clip']['tracks'][0]['auxiliary_f32']
        for obj in sample['objects']:
            slot=obj['slot']
            if slot in (9,10,20) or 'linked_local_matrix' not in obj:continue
            if obj['linked_local_matrix_flags']&8:raise ValueError('Scaled local unsupported')
            matrices=[]
            for values in operands:
                value=values.get(slot,{})
                if 'quaternion_xyzw' not in value or 'position_xyz' not in value:break
                matrix=_quaternion_matrix(value['quaternion_xyzw']);matrix[12:15]=value['position_xyz'];matrices.append(matrix)
            if len(matrices)!=2:continue
            rows.append(dict(slot=slot,incoming=matrices[0],saved_primary=matrices[1],weight=weight,
                             observed=obj['linked_local_matrix']))
            provenance.append(dict(sample=sample['index'],slot=slot,source_keys=keys))
    report_path('stage43-bevy-local-blend-native.json').write_text(json.dumps(rows,indent=2))
    report_path('stage43-bevy-local-blend-provenance.json').write_text(json.dumps(dict(
        source=str(args.snapshot),sha256=hashlib.sha256(args.snapshot.read_bytes()).hexdigest(),rows=provenance,
        limitations=['Source operands reconstructed; observed output comes from qualified native reads.',
                    'Tracking slots excluded; root translation excluded from comparisons.',
                    'This is local pose math validation, not Bevy skeleton/render parity.']),indent=2))
    print('fixture cases',len(rows))


if __name__=='__main__':main()
