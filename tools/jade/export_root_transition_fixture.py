"""Complete slot0 source/reference operands; observed outputs remain independent."""
import json,hashlib
from pathlib import Path
from project_paths import ASSET_ROOT,report_path
from probe_transition_pose import channels

def main():
    basis_path=report_path('stage43-tracking-sequence-20261009-023957-root-rotation.json')
    basis=json.loads(basis_path.read_text())
    sequence_path=report_path('stage43-tracking-sequence-20261009-023957.json')
    samples={s['index']:s for s in json.loads(sequence_path.read_text())['samples']}
    sources={};cases=[]
    for row in basis['cases']:
        sample=samples[row['sample']];operands=[]
        for op in row['operands']:
            key=op['source']
            if key not in sources:sources[key]=json.loads((ASSET_ROOT/f'animations/sally/local-samples/{key}.json').read_text())
            values,missing=channels(sources[key],sample[op['instance']+'_clip']['tracks'])
            if missing:raise ValueError('Previously qualified channels no longer supported')
            value=values.get(0,{})
            operands.append(dict(op,position=value.get('position_xyz')))
        cases.append(dict(sample=row['sample'],operands=operands,weight=row.get('weight'),observed=row['observed'],height=sample['component_height_b4'],add_height=bool(int(sample['actor']['flags'],16)&2)))
    output=report_path('stage43-root-transition-native.json')
    output.write_text(json.dumps(dict(source=str(sequence_path),sha256=hashlib.sha256(sequence_path.read_bytes()).hexdigest(),source_basis_report=str(basis_path),cases=cases,
        limitations=['Sequential postframe actor/reference inputs are conditional, not callback inputs. All prior qualified root basis cases retained; no predicted error filtering. Position comparisons require complete channels in all operands.'])))
    print(json.dumps(dict(report=str(output),cases=len(cases),positions=sum(all(o['position'] is not None for o in c['operands']) for c in cases))))
if __name__=='__main__':main()
