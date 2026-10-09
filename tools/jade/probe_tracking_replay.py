"""Conditional primary-only tracking replay from explicit adjacent snapshots.

No final corrected role local is used as its ordinary animation input. Prior
world is a scheduling candidate rebuilt from earlier final locals with current
actor world, not asserted to be the actual native callback input.
"""
import argparse
import json
import math
import struct
from copy import deepcopy
from pathlib import Path
from jade_trace_consistency import pair_candidate
from audit_tracking_trace import input_rejection_reasons
from match_sally_runtime_clip import signature
from probe_transition_pose import channels
from jade_target_hierarchy import snapshot_target_nodes, linked_target_position
from jade_tracking_local import compose_tracking_world
from jade_modifier24 import _quaternion_matrix
from jade_actor_reference import actor_reference_position
from jade_tracking_call import tracking_arguments
from jade_tracking_limits import tracking_limits
from jade_tracking_phase import tracking_phase_gate
from jade_tracking_target_gate import tracking_target_gate
from jade_tracking_target_selection import select_tracking_target
from jade_tracking_step import tracking_step
from jade_animation_transition import f32
from project_paths import ASSET_ROOT,report_path


def ordinary_nodes(sample,source):
    nodes=snapshot_target_nodes(sample)
    values,missing=channels(source,sample['primary_clip']['tracks'])
    if missing:raise ValueError('Unsupported ordinary animation channel')
    actor=sample['actor']['world_matrix'];actor_flags=int(sample['actor']['flags'],16)
    if actor_flags&0x400000:raise NotImplementedError('Linked actor reference')
    ref=struct.unpack('<16fI',bytes.fromhex(sample['actor_reference_matrix_hex']))
    for obj in sample['objects']:
        slot=obj['slot'];address=int(obj['address'],16)
        if slot not in values:continue
        if 'local_matrix' not in nodes[address]:raise ValueError('Animated node local absent')
        matrix=nodes[address]['local_matrix'];value=values[slot]
        if nodes[address]['local_flags']&8:raise NotImplementedError('Scaled animated node')
        if 'quaternion_xyzw' in value:
            rotation=_quaternion_matrix(value['quaternion_xyzw'])
            for i in (0,1,2,4,5,6,8,9,10):matrix[i]=rotation[i]
        if 'position_xyz' in value:
            position=value['position_xyz']
            if slot==0:
                position=actor_reference_position(position,ref[:16],ref[16],actor[:16],int(actor[16]),
                    height=sample['component_height_b4'],add_height=bool(actor_flags&2))
            matrix[12:15]=position
    return nodes,values


def main():
    parser=argparse.ArgumentParser();parser.add_argument('snapshot',type=Path)
    args=parser.parse_args();samples=json.loads(args.snapshot.read_text())['samples']
    sources={}
    for path in sorted((ASSET_ROOT/'animations/sally/local-samples').glob('*.json')):
        source=json.loads(path.read_text())
        sources.setdefault(json.dumps(signature(source['tracks'])),[]).append((path.stem,source))
    rows=[];skipped=[]
    for first,second in zip(samples,samples[1:]):
        if not pair_candidate(first,second)['candidate']:continue
        try:
            if input_rejection_reasons(first)+input_rejection_reasons(second):raise ValueError('Unstable tracking inputs')
            if second['component_flags_u16']>>8&15!=1:raise NotImplementedError('Active transition tracking phase')
            if not first.get('object_prefixes_unchanged') or not second.get('object_prefixes_unchanged'):
                raise ValueError('Object prefix changed or unavailable')
            if not first.get('pose_matrices_unchanged') or not second.get('pose_matrices_unchanged'):
                raise ValueError('Whole-pose matrix recheck changed or unavailable')
            candidates=sources.get(json.dumps(signature(second['primary_clip']['tracks'],True)),[])
            if len(candidates)!=1:raise ValueError('Primary source not unique')
            key,source=candidates[0];nodes,values=ordinary_nodes(second,source)
            actor=int(second['actor']['address'],16)
            roles={role:int(second['objects'][second['tracking_role_tags'].index(role)]['address'],16) for role in (0,1,12)}
            slots={role:second['tracking_role_tags'].index(role) for role in roles}
            if not all(slots[role] in values for role in roles):raise ValueError('Ordinary role animation missing')
            old_nodes=snapshot_target_nodes(first)
            old_nodes[actor]['world_matrix']=list(second['actor']['world_matrix'][:16])
            old_nodes[actor]['world_flags']=int(second['actor']['world_matrix'][16])
            continuity=int(second['objects'][0]['address'],16)
            previous={address:compose_tracking_world(old_nodes,address) for address in (*roles.values(),continuity)}
            raw=bytes.fromhex(second['brain_604_61f_hex'])
            base,target_handle=struct.unpack_from('<2I',raw);offset=struct.unpack_from('<3f',raw,8)
            word,strength=struct.unpack_from('<If',raw,20)
            resolved=int(second['target_resolved_address'],16)
            if resolved not in (0,actor):raise NotImplementedError('Other target actor inputs absent')
            globals_=second['tracking_inputs']
            target_gate=tracking_target_gate(resolved,[int(v,16) for v in globals_['blocked_targets']],second['current_phase_flags'])
            target=select_tracking_target(word,offset,second['actor']['world_matrix'][12:15],
                target_enabled=target_gate['target_enabled'],target_is_self=resolved==actor,
                role0_position=linked_target_position(nodes,roles[0])['position'])
            call=tracking_arguments(base,target['tracking_word'],strength,second['delta_time'],
                globals_['strength_multiplier'],target_enabled=target_gate['target_enabled'])
            phase=tracking_phase_gate(first['tracking_counter_af'],call['strength'],second['delta_time'],
                current_flags=second['current_phase_flags'],phase_control=second['current_phase_control'])
            if not phase['continue']:raise NotImplementedError('Phase skips tracking writes')
            if not call['parameter_10']:roles.pop(12)
            overrides=({address.removeprefix('0x'):value for address,value in globals_['limit_overrides'].items()}
                       if call['parameter_9'] else None)
            limits=tracking_limits(call['mode'],secondary=bool(call['parameter_10']),overrides=overrides,
                unrestricted=bool(call['parameter_6']))
            result=tracking_step(nodes,actor,roles,previous,continuity,strength=phase['strength'],
                limits=limits,sign_axis=globals_['sign_axis'],allow_limit_crossing=bool(call['parameter_5']),
                scale_references=([1.,1.,1.],[0.,0.,0.]),coefficients=lambda a:(f32(math.cos(a)),f32(math.sin(a))),
                target=target['target'],phase_blocked=not bool(second['current_phase_flags']&4),
                parameter7=bool(call['parameter_7']),parameter8=bool(call['parameter_8']))
            for role,address in roles.items():
                actual=second['objects'][slots[role]]['linked_local_matrix'];expected=result['nodes'][address]['local_matrix']
                rows.append(dict(first=first['index'],second=second['index'],key=key,role=role,slot=slots[role],
                    rotation_error=max(abs(expected[i]-actual[i]) for i in (0,1,2,4,5,6,8,9,10)),
                    position_error=max(abs(expected[i]-actual[i]) for i in (12,13,14)),
                    target_branch=target['branch'],desired_branch=result['desired']['branch'],
                    callback_inputs_proven=False))
        except (ValueError,NotImplementedError) as error:
            skipped.append(dict(first=first['index'],second=second['index'],reason=str(error)))
    result=dict(snapshot=str(args.snapshot),rows=rows,skipped=skipped,
        limitations=['Prior worlds rebuilt from earlier final locals are conditional scheduling candidates.',
                    'Primary-only self/null target; modifier write gates and current callback ownership not traced.',
                    'Unanimated locals supplied from current snapshot; scale reference constants and host trig are conditional.',
                    'No proof of full tracking, transition or Bevy/native pose parity.'])
    for field in ('rotation','position'):
        errors=[row[field+'_error'] for row in rows]
        result[field]=dict(checked=len(errors),matched=sum(e<=1e-5 for e in errors),maximum_error=max(errors,default=None))
    report_path(args.snapshot.stem+'-tracking-replay.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','skipped')}))
    print('skipped',len(skipped))


if __name__=='__main__':main()
