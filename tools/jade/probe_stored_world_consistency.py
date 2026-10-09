"""Compare saved stored world with world rebuilt from the SAME saved locals.

This detects disagreement; it never identifies prior callback inputs.
"""
import argparse
import json
from collections import Counter
from pathlib import Path
from jade_trace_consistency import rejection_reasons
from jade_target_hierarchy import snapshot_target_nodes
from jade_tracking_local import compose_tracking_world
from project_paths import report_path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('snapshot',type=Path)
    args=parser.parse_args();sequence=json.loads(args.snapshot.read_text())
    rows=[];skipped=[]
    for sample in sequence['samples']:
        if rejection_reasons(sample):continue
        nodes=snapshot_target_nodes(sample)
        for obj in sample['objects']:
            try:
                matrix,_=compose_tracking_world(nodes,int(obj['address'],16))
                actual=obj['matrix']
                rows.append(dict(sample=sample['index'],slot=obj['slot'],
                    basis_error=max(abs(matrix[i]-actual[i]) for i in (0,1,2,4,5,6,8,9,10)),
                    position_error=max(abs(matrix[i]-actual[i]) for i in (12,13,14))))
            except (ValueError,NotImplementedError) as error:
                skipped.append(dict(sample=sample['index'],slot=obj['slot'],reason=str(error)))
    result=dict(snapshot=str(args.snapshot),rows=rows,skipped=skipped,
        limitation='Post-update matrix agreement or disagreement does not establish callback input age; scale normalization not modeled.')
    for field in ('basis','position'):
        errors=[row[field+'_error'] for row in rows]
        result[field]=dict(checked=len(errors),matched=sum(e<=1e-5 for e in errors),maximum_error=max(errors,default=None))
        result[field]['failure_slots']=dict(Counter(row['slot'] for row in rows if row[field+'_error']>1e-5))
    report_path(args.snapshot.stem+'-stored-world-consistency.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','skipped')}))
    print('skipped',len(skipped))


if __name__=='__main__':main()
