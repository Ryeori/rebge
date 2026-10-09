"""Conditional replay at observed source-local publication boundaries.

Previous observed worlds are explicit inputs, never final output used as an
ordinary pose seed. Sampling does not establish native callback entry.
"""
import argparse
import json
import math
import struct
from copy import deepcopy
from pathlib import Path
from jade_animation_transition import f32
from jade_modifier24 import _quaternion_matrix
from jade_tracking_call import tracking_arguments
from jade_tracking_limits import tracking_limits
from jade_tracking_phase import tracking_phase_gate
from jade_tracking_target_gate import tracking_target_gate
from jade_tracking_target_selection import select_tracking_target
from jade_target_hierarchy import linked_target_position
from jade_tracking_step import tracking_step
from jade_tracking_window import window_input_rejections
from match_sally_runtime_clip import signature
from probe_tracking_replay import ordinary_nodes
from probe_transition_pose import channels
from project_paths import ASSET_ROOT,report_path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('snapshot',type=Path)
    args=parser.parse_args();record=json.loads(args.snapshot.read_text());observations=record['rows']
    full=json.loads(Path(record['source_snapshot']).read_text())['samples']
    templates=[s for s in full if s['primary_clip']['resource_address']==record['primary_resource_address']]
    if not templates and 'primary_clip' not in record:raise ValueError('Clip absent from full sequence')
    template=deepcopy(templates[-1] if templates else full[-1])
    if 'primary_clip' in record:template['primary_clip']=record['primary_clip']
    tracks=template['primary_clip']['tracks']
    candidates=[]
    for path in (ASSET_ROOT/'animations/sally/local-samples').glob('*.json'):
        source=json.loads(path.read_text())
        if signature(source['tracks'])==signature(tracks,True):candidates.append((path.stem,source))
    if len(candidates)!=1:raise ValueError('Unique source required')
    key,source=candidates[0]
    def matrix(row,name):return struct.unpack('<16fI',bytes.fromhex(row['matrices'][name]))
    prepared=[]
    for index,row in enumerate(observations):
        if not row['primary_clip_unchanged'] or not row.get('tracking_inputs_unchanged'):
            prepared.append(None);continue
        states=deepcopy(tracks)
        for i,state in enumerate(states):
            elapsed,aux,frame,flags=struct.unpack_from('<ffHH',bytes.fromhex(row['primary_states_hex']),i*12)
            state.update(elapsed_seconds=elapsed,auxiliary_f32=aux,frame_index=frame,state_flags=flags)
        values,missing=channels(source,states)
        if missing:prepared.append(None);continue
        errors=[]
        for slot in (9,10,20):
            if 'quaternion_xyzw' not in values.get(slot,{}):break
            expected=_quaternion_matrix(values[slot]['quaternion_xyzw']);actual=matrix(row,f'{slot}_local')
            errors.append(max(abs(expected[i]-actual[i]) for i in (0,1,2,4,5,6,8,9,10)))
        prepared.append(dict(states=states,ordinary=len(errors)==3 and max(errors)<=1e-5))
    rows=[];skipped=[]
    for index in range(1,len(observations)):
        before,current=observations[index-1:index+1];ready=prepared[index]
        if ready is None or not ready['ordinary']:continue
        if prepared[index-1] is None or prepared[index-1]['ordinary']:continue
        if before['pass_before']!=before['pass_after'] or current['pass_before']!=current['pass_after']:continue
        try:
            sample=deepcopy(template);sample['primary_clip']['tracks']=ready['states']
            sample['actor']['world_matrix']=list(matrix(current,'actor_world'))
            sample['delta_time']=current['delta_time']
            if 'current_phase_flags' in current:
                if current['component_flags_u16']>>8&15!=1:raise ValueError('Primary-only component required')
                sample['actor']['flags']=current['actor_flags']
                sample['actor_reference_matrix_hex']=current['actor_reference_matrix_hex']
                sample['component_height_b4']=current['component_height_b4']
            prefix=bytes.fromhex(current['component_aa_b5_hex']);phase_index=prefix[2]
            # Legacy full records lack the component phase index. The primary
            # instance phase is only a conditional proxy, not validated input.
            phase_samples=[s for s in templates if s.get('current_phase_flags') is not None
                and bytes.fromhex(s['primary_header_hex'])[0x56]==phase_index]
            if 'current_phase_flags' in current:
                if current['current_phase_flags'] is None:raise ValueError('Observed phase unavailable')
                phase_template=current
            else:
                if not phase_samples:raise ValueError('Phase flags unavailable for observed phase')
                phase_template=phase_samples[-1]
            raw=bytes.fromhex(current['brain_604_61f_hex']);base,handle=struct.unpack_from('<2I',raw)
            if current['target_reference']!=template['target_reference']:
                raise ValueError('Target storage reference changed')
            if handle!=struct.unpack_from('<I',bytes.fromhex(template['brain_604_61f_hex']),4)[0]:
                raise ValueError('Target handle changed')
            offset=struct.unpack_from('<3f',raw,8);word,strength=struct.unpack_from('<If',raw,20)
            nodes,_=ordinary_nodes(sample,source);actor=int(sample['actor']['address'],16)
            roles={role:int(sample['objects'][sample['tracking_role_tags'].index(role)]['address'],16) for role in (0,1,12)}
            slots={role:sample['tracking_role_tags'].index(role) for role in roles}
            # Preserve source inputs; only unanimated channels rely on template.
            continuity=int(sample['objects'][0]['address'],16)
            previous={address:(list(matrix(before,f'{slots[role]}_world')[:16]),matrix(before,f'{slots[role]}_world')[16])
                      for role,address in roles.items()}
            previous[continuity]=(list(matrix(before,'0_world')[:16]),matrix(before,'0_world')[16])
            inputs=deepcopy(sample['tracking_inputs']);resolved=int(sample['target_resolved_address'],16)
            if 'sign_axis' in current:
                inputs.update(sign_axis=current['sign_axis'],strength_multiplier=current['strength_multiplier'])
            if resolved not in (0,actor):raise NotImplementedError('Other actor target')
            gate=tracking_target_gate(resolved,[int(x,16) for x in inputs['blocked_targets']],phase_template['current_phase_flags'])
            target=select_tracking_target(word,offset,sample['actor']['world_matrix'][12:15],
                target_enabled=gate['target_enabled'],target_is_self=resolved==actor,
                #140e02760 ->140b33020 evaluates current linked locals.
                role0_position=linked_target_position(nodes,roles[0])['position'])
            call=tracking_arguments(base,target['tracking_word'],strength,current['delta_time'],
                inputs['strength_multiplier'],target_enabled=gate['target_enabled'])
            phase=tracking_phase_gate(bytes.fromhex(before['component_aa_b5_hex'])[5],call['strength'],current['delta_time'],
                current_flags=phase_template['current_phase_flags'],phase_control=phase_template['current_phase_control'])
            if not phase['continue']:raise ValueError('Phase skips tracking')
            if call['parameter_9']:raise NotImplementedError('Live limit overrides not observed')
            if not call['parameter_10']:roles.pop(12)
            result=tracking_step(nodes,actor,roles,previous,continuity,strength=phase['strength'],
                limits=tracking_limits(call['mode'],secondary=bool(call['parameter_10']),unrestricted=bool(call['parameter_6'])),
                sign_axis=inputs['sign_axis'],allow_limit_crossing=bool(call['parameter_5']),
                scale_references=([1.,1.,1.],[0.,0.,0.]),coefficients=lambda a:(f32(math.cos(a)),f32(math.sin(a))),
                target=target['target'],phase_blocked=not bool(phase_template['current_phase_flags']&4),
                parameter7=bool(call['parameter_7']),parameter8=bool(call['parameter_8']))
            # Local role0 is restored last. Sequential reads can still mix
            # earlier secondary locals with later role0. Require another
            # observation with identical role locals; never select by error.
            after_index=None
            for next_index in range(index+1,min(index+12,len(observations)-1)):
                after=observations[next_index]
                if after['primary_states_hex']!=current['primary_states_hex']:break
                repeated=observations[next_index+1]
                if (after['primary_clip_unchanged'] and repeated['primary_clip_unchanged']
                    and repeated['primary_states_hex']==current['primary_states_hex']
                    and after['matrices']['20_local']!=current['matrices']['20_local']
                    and all(after['matrices'][f'{slot}_local']==repeated['matrices'][f'{slot}_local']
                            for slot in (9,10,20))):
                    after_index=next_index;break
            if after_index is None:raise ValueError('No following role0 write with same clip state')
            after=observations[after_index]
            window_rejections=window_input_rejections(current,after,observations[after_index+1])
            for role,address in roles.items():
                expected=result['nodes'][address]['local_matrix'];actual=matrix(after,f'{slots[role]}_local')
                rows.append(dict(before=index-1,ordinary=index,after=after_index,role=role,
                    window_input_rejections=window_rejections,
                    phase_inputs_observed='current_phase_flags' in current,
                    rotation_error=max(abs(expected[i]-actual[i]) for i in (0,1,2,4,5,6,8,9,10)),
                    position_error=max(abs(expected[i]-actual[i]) for i in (12,13,14))))
        except (ValueError,NotImplementedError) as error:skipped.append(dict(index=index,reason=str(error)))
    summary=dict(source_key=key,checked=len(rows),matched=sum(x['rotation_error']<=1e-5 for x in rows),
        maximum_rotation_error=max((x['rotation_error'] for x in rows),default=None),
        positions_matched=sum(x['position_error']<=1e-5 for x in rows),
        maximum_position_error=max((x['position_error'] for x in rows),default=None),
        phase_observed_comparisons=sum(x['phase_inputs_observed'] for x in rows))
    summary['stable_input_window_comparisons']=sum(not x['window_input_rejections'] for x in rows)
    summary['stable_input_window_matches']=sum(not x['window_input_rejections'] and x['rotation_error']<=1e-5 for x in rows)
    result=dict(summary=summary,rows=rows,skipped=skipped,
        limitations=['Sequential observations do not prove callback-entry matrices.',
                    'Older recordings use a conditional instance-phase proxy/full-template reference and globals.',
                    'Blocked targets, target resolution and unanimated nodes remain full-template inputs; not all pointer lifetimes checked.',
                    'Primary-only, self/null target, no scaled branch; host transcendental functions.',
                    'No best-fitting observation selected and no native/Bevy parity claim.'])
    report_path(args.snapshot.stem+'-conditional-replay.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(summary));print('skipped',len(skipped))


if __name__=='__main__':main()
