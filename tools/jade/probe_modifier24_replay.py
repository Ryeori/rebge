"""Conditional adjacent-pass replay; never promotes final samples to inputs."""
import argparse
import json
import struct
from pathlib import Path
from jade_trace_consistency import pair_candidate
from jade_modifier24 import modifier24_step
from jade_target_hierarchy import raw_affine_product
from jade_basis_normalize import normalize_basis
from project_paths import report_path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('snapshot',type=Path)
    args=parser.parse_args();samples=json.loads(args.snapshot.read_text())['samples']
    rows=[];skipped=[]
    for first,second in zip(samples,samples[1:]):
        if not pair_candidate(first,second)['candidate']:continue
        if not all(s.get('modifier24_states_unchanged') and s.get('object_prefixes_unchanged') for s in (first,second)):continue
        old={o['slot']:o for o in first['objects']};objects={o['address']:o for o in second['objects']}
        obj=next(o for o in second['objects'] if o['slot']==28)
        try:
            previous=old[28].get('modifier24_records',[]);current=obj.get('modifier24_records',[])
            if len(previous)!=1 or len(current)!=1:raise ValueError('Expected one modifier24 per slot28')
            if previous[0]['address']!=current[0]['address']:raise ValueError('Modifier instance changed')
            parent=objects.get(obj['linked_parent_address'])
            if parent is None:raise ValueError('Parent world absent')
            prior=bytearray.fromhex(previous[0]['state_hex']);observed=bytes.fromhex(current[0]['state_hex'])
            # Native1409ddef0 copies the local before1409dcba0. This uses a
            # captured final local as a conditional candidate, not proven input.
            struct.pack_into('<16fI',prior,0xc,*obj['linked_local_matrix'],obj['linked_local_matrix_flags'])
            nominal,flags=raw_affine_product(obj['linked_local_matrix'],parent['matrix'],
                obj['linked_local_matrix_flags'],parent['matrix_flags'])
            replay=modifier24_step(prior,nominal,flags,parent['matrix'],parent['matrix_flags'],second['delta_time'])
            predicted=struct.unpack_from('<3f',replay['state_bytes'],0x88)
            actual=struct.unpack_from('<3f',observed,0x88)
            matrix=normalize_basis(replay['world_matrix'])
            rows.append(dict(first=first['index'],second=second['index'],weight=replay['weight'],
                current_cycle_marker_set=bool(struct.unpack_from('<I',observed,4)[0]&0x10000000),
                state_position_error=max(abs(a-b) for a,b in zip(predicted,actual)),
                published_basis_error=max(abs(matrix[i]-obj['matrix'][i]) for i in (0,1,2,4,5,6,8,9,10)),
                callback_input_proven=False))
        except (ValueError,NotImplementedError) as error:
            skipped.append(dict(first=first['index'],second=second['index'],reason=str(error)))
    result=dict(snapshot=str(args.snapshot),rows=rows,skipped=skipped,
        limitations=['Adjacent pass readings are candidates, not proven prior callback state.',
                    'Current final local/parent world and captured delta are conditional writer inputs.',
                    'Palette publication reconstructed by basis normalization, not exact native palette pass.'])
    for field in ('state_position','published_basis'):
        errors=[r[field+'_error'] for r in rows]
        result[field]=dict(checked=len(errors),matched=sum(e<=1e-5 for e in errors),maximum_error=max(errors,default=None))
        completed=[r[field+'_error'] for r in rows if not r['current_cycle_marker_set']]
        result[field]['cycle_marker_clear']=dict(checked=len(completed),matched=sum(e<=1e-5 for e in completed),maximum_error=max(completed,default=None))
    report_path(args.snapshot.stem+'-modifier24-replay.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','skipped')}))
    print('skipped',len(skipped))


if __name__=='__main__':main()
