"""Check saved publication relation1409ce210, not tracking input chronology."""
import argparse
import json
from pathlib import Path
from jade_target_hierarchy import raw_affine_product
from project_paths import report_path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('snapshot',type=Path)
    args=parser.parse_args();s=json.loads(args.snapshot.read_text())
    actor=s['actor']['world_matrix'];rows=[];skipped=[]
    for obj,palette in zip(s['objects'],s['palette']['matrices']):
        slot=obj['slot']
        try:
            if obj.get('update_flags_u32',0)&0x80000000:
                raise ValueError('Native world write disabled by negative update flags')
            expected,flags=raw_affine_product(palette['matrix'],actor[:16],palette['flags'],int(actor[16]))
            observed=obj['matrix']
            rows.append(dict(slot=slot,basis_error=max(abs(expected[i]-observed[i])
                for i in (0,1,2,4,5,6,8,9,10)),
                position_error=max(abs(expected[i]-observed[i]) for i in (12,13,14))))
        except (ValueError,NotImplementedError) as error:
            skipped.append(dict(slot=slot,reason=str(error)))
    result=dict(snapshot=str(args.snapshot),checked=len(rows),skipped=skipped,rows=rows,
        matched=sum(max(r['basis_error'],r['position_error'])<=1e-5 for r in rows),
        maximum_basis_error=max((r['basis_error'] for r in rows),default=None),
        maximum_position_error=max((r['position_error'] for r in rows),default=None),
        limitations=['Saved actor*palette relation only; does not identify world inputs at callback entry.',
                    'No-scale finite branch; no native frame or callback trace.'])
    report_path(args.snapshot.stem+'-palette-world.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))


if __name__=='__main__':main()
