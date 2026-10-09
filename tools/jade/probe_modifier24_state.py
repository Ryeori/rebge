"""Compare observed modifier state with published world; not a dynamics replay."""
import argparse
import json
import struct
from pathlib import Path
from jade_trace_consistency import rejection_reasons
from project_paths import report_path
from jade_modifier24 import effective_mode_flags,lag_pose_from_position
from jade_target_hierarchy import raw_affine_product
from jade_basis_normalize import normalize_basis


def main():
    parser=argparse.ArgumentParser();parser.add_argument('snapshot',type=Path)
    args=parser.parse_args();saved=json.loads(args.snapshot.read_text())
    sequence='samples' in saved;samples=saved['samples'] if sequence else [saved]
    rows=[];skipped=[]
    for sample in samples:
        if sequence and (rejection_reasons(sample) or not sample.get('modifier24_states_unchanged')):continue
        if not sequence and not sample.get('pose_consistency',{}).get('modifier24_states_unchanged'):continue
        objects={obj['address']:obj for obj in sample['objects']}
        for obj in sample['objects']:
            for record in obj.get('modifier24_records',[]):
                try:
                    if not record['header_unchanged'] or not record['state_unchanged']:raise ValueError('Mutable modifier state')
                    raw=bytes.fromhex(record['state_hex'])
                    if len(raw)!=256:raise ValueError('Unexpected modifier-state size')
                    mode=struct.unpack_from('<I',raw,4)[0];flags=record['record_flags']
                    if flags&0xa000000 or not flags&0x1000000:raise ValueError('Modifier execution disabled')
                    if mode&0x1000:raise NotImplementedError('Alternate modifier evaluator')
                    row=dict(sample=sample.get('index'),slot=obj['slot'],mode_flags=hex(mode),
                        damping=struct.unpack_from('<f',raw,8)[0],record_flags=hex(flags),
                        modifier_address=record['address'])
                    effective=effective_mode_flags(mode,bool(int(obj.get('linked_parent_address','0'),16)))
                    row['effective_mode_flags']=hex(effective)
                    saved_local=struct.unpack_from('<16fI',raw,0xc)
                    if 'linked_local_matrix' in obj:
                        row['restored_local_error']=max(abs(a-b) for a,b in zip(saved_local[:16],obj['linked_local_matrix']))
                        row['cycle_marker_set']=bool(mode&0x10000000)
                    if effective&2:
                        expected=struct.unpack_from('<16f',raw,0x58)
                        row['basis_error']=max(abs(expected[i]-obj['matrix'][i]) for i in (0,1,2,4,5,6,8,9,10))
                    if effective&9:
                        expected=struct.unpack_from('<3f',raw,0x88)
                        row['position_error']=max(abs(a-b) for a,b in zip(expected,obj['matrix'][12:15]))
                        if effective&8 and obj.get('linked_parent_address') in objects:
                            parent=objects[obj['linked_parent_address']]
                            nominal,nominal_flags=raw_affine_product(obj['linked_local_matrix'],parent['matrix'],
                                obj['linked_local_matrix_flags'],parent['matrix_flags'])
                            corrected,_=lag_pose_from_position(nominal,nominal_flags,parent['matrix'],expected)
                            corrected=normalize_basis(corrected)
                            row['lag_basis_error']=max(abs(corrected[i]-obj['matrix'][i]) for i in (0,1,2,4,5,6,8,9,10))
                    rows.append(row)
                except (ValueError,NotImplementedError) as error:
                    skipped.append(dict(sample=sample.get('index'),slot=obj['slot'],reason=str(error)))
    result=dict(snapshot=str(args.snapshot),rows=rows,skipped=skipped,
        limitation='State-to-published-world check only; no proof of previous state, callback execution count or full dynamics parity.')
    for field in ('basis','position','lag_basis','restored_local'):
        errors=[r[field+'_error'] for r in rows if field+'_error' in r]
        result[field]=dict(checked=len(errors),matched=sum(e<=1e-5 for e in errors),maximum_error=max(errors,default=None))
    report_path(args.snapshot.stem+'-modifier24-state.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','skipped')}))
    print('skipped',len(skipped))


if __name__=='__main__':main()
