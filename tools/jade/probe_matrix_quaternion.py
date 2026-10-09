"""Saved-matrix numerical round trip; no final pose/native quaternion oracle."""
import argparse
import json
from jade_matrix_quaternion import matrix_quaternion
from jade_pose import rotation_matrix
from project_paths import report_path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('snapshot')
    args=parser.parse_args()
    with open(args.snapshot) as stream: sequence=json.load(stream)
    seen=set();rows=[];skipped=0
    for sample in sequence['samples']:
        for obj in sample['objects']:
            for kind,field,flag in [('world','matrix','matrix_flags'),
                                   ('local','linked_local_matrix','linked_local_matrix_flags')]:
                if field not in obj or obj.get(flag,0)&8:
                    skipped+=1
                    continue
                matrix=obj[field];signature=(kind,tuple(matrix))
                if signature in seen:continue
                seen.add(signature)
                rebuilt=rotation_matrix(matrix_quaternion(matrix))
                error=max(abs(matrix[i]-rebuilt[i]) for i in (0,1,2,4,5,6,8,9,10))
                rows.append(dict(sample=sample['index'],slot=obj['slot'],kind=kind,basis_error=error))
    result=dict(source=args.snapshot,distinct_matrices=len(rows),skipped_scaled_or_missing=skipped,
        world_maximum_basis_error=max(r['basis_error'] for r in rows if r['kind']=='world'),
        local_maximum_basis_error=max(r['basis_error'] for r in rows if r['kind']=='local'),
        limitations=['Saved basis round trip only; native quaternion output and final pose unverified.',
                     'Rebuild uses numerical rotation_matrix; not native bit-exact parity.'],
        worst_rows=sorted(rows,key=lambda r:r['basis_error'],reverse=True)[:8])
    report_path('stage43-matrix-quaternion-roundtrip.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps(result))


if __name__=='__main__':main()
