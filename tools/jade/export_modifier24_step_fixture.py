"""Conditional prior-state/native output fixture; fixed completed-cycle selection."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from jade_trace_consistency import pair_candidate
from jade_target_hierarchy import raw_affine_product,snapshot_target_nodes
from project_paths import ASSET_ROOT


def main():
    parser=argparse.ArgumentParser();parser.add_argument('sequence',type=Path);args=parser.parse_args()
    raw=args.sequence.read_bytes();samples=json.loads(raw)['samples'];cases=[];skipped=[]
    rig_path=ASSET_ROOT/'skeletons/sally/gao-parent-links.json';rig_raw=rig_path.read_bytes();rig=json.loads(rig_raw)
    bone_indices={o['slot']:i for i,o in enumerate(rig['objects']) if o['slot'] is not None}
    for a,b in zip(samples,samples[1:]):
        reasons=pair_candidate(a,b)['reasons']
        for sample in (a,b):
            if not sample.get('modifier24_states_unchanged') or not sample.get('object_prefixes_unchanged'):
                reasons.append('modifier_or_object_changed')
        old={o['slot']:o for o in a['objects']};current={o['slot']:o for o in b['objects']}
        obj=current[28];prior=old[28].get('modifier24_records',[]);records=obj.get('modifier24_records',[])
        if len(prior)!=1 or len(records)!=1:reasons.append('modifier_count')
        elif prior[0]['address']!=records[0]['address']:reasons.append('modifier_instance_changed')
        if records and struct.unpack_from('<I',bytes.fromhex(records[0]['state_hex']),4)[0]&0x10000000:
            reasons.append('after_sample_inside_processed_cycle')
        parent=next((o for o in b['objects'] if o['address']==obj.get('linked_parent_address')),None)
        if parent is None:reasons.append('parent_missing')
        if reasons:
            skipped.append(dict(before=a['index'],after=b['index'],reasons=sorted(set(reasons))));continue
        state=bytearray.fromhex(prior[0]['state_hex'])
        struct.pack_into('<16fI',state,0xc,*obj['linked_local_matrix'],obj['linked_local_matrix_flags'])
        nominal,flags=raw_affine_product(obj['linked_local_matrix'],parent['matrix'],
            obj['linked_local_matrix_flags'],parent['matrix_flags'])
        observed=bytes.fromhex(records[0]['state_hex'])
        cycle_reasons=[];cycle_records=[]
        for slot in (27,28):
            states=old[slot].get('modifier24_records',[])
            if len(states)!=1:
                cycle_reasons.append('cycle_modifier_count');continue
            data=bytes.fromhex(states[0]['state_hex'])
            if struct.unpack_from('<I',data,4)[0]&0x10000000:cycle_reasons.append('prior_cycle_unfinished')
            cycle_records.append(dict(bone=bone_indices[slot],state_hex=data.hex(),record_flags=states[0]['record_flags']))
        nodes=snapshot_target_nodes(b)
        serialized=[dict(address=address,flags=n['flags'],world=n['world_matrix'],world_flags=n['world_flags'],
            parent=n.get('parent_address'),local=n.get('local_matrix'),local_flags=n.get('local_flags'))
            for address,n in nodes.items()]
        actor=int(b['actor']['address'],16)
        mapping=[int(current[bone['slot']]['address'],16) if bone['slot'] is not None else actor for bone in rig['objects']]
        cases.append(dict(before=a['index'],after=b['index'],state_hex=state.hex(),
            nominal=nominal,nominal_flags=flags,parent=parent['matrix'],parent_flags=parent['matrix_flags'],
            delta=b['delta_time'],observed_position=list(struct.unpack_from('<3f',observed,0x88)),
            observed_world=obj['matrix'],observed_world_flags=obj['matrix_flags'],
            current_local=obj['linked_local_matrix'],current_local_flags=obj['linked_local_matrix_flags'],
            observed_state_hex=observed.hex(),
            cycle_inputs_available=not cycle_reasons,cycle_input_reasons=cycle_reasons,
            cycle_records=cycle_records,nodes=serialized,bone_addresses=mapping,
            requested_bone=bone_indices[28],parent_modifier_bone=bone_indices[27],
            cycle_expected=[dict(bone=bone_indices[slot],slot=slot,world=current[slot]['matrix'],
                local=current[slot]['linked_local_matrix'],local_flags=current[slot]['linked_local_matrix_flags'])
                for slot in (27,28)]))
    result=dict(source_sequence=str(args.sequence),source_sha256=hashlib.sha256(raw).hexdigest(),cases=cases,skipped=skipped,
        source_rig=str(rig_path),source_rig_sha256=hashlib.sha256(rig_raw).hexdigest(),
        selection='All guarded adjacent pairs with one stable slot28 modifier and completed after-cycle marker.',
        limitations=['Prior state and current restored local/parent are conditional writer inputs; callback age unproven.',
                     'Native observed state/world are independent outputs; no predicted-error filtering.',
                     'Observed final basis includes downstream publication/normalization stages.'])
    path=args.sequence.with_name(args.sequence.stem+'-modifier24-step-native.json');path.write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(report=str(path),cases=len(cases),skipped=len(skipped))))


if __name__=='__main__':main()
