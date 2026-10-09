"""Compare reconstructed target points to stored world translations."""
import argparse
import json
from pathlib import Path

from jade_target_hierarchy import linked_target_position, snapshot_target_nodes
from jade_tracking_target_selection import select_tracking_target
from jade_tracking_call import tracking_arguments
from jade_tracking_target_gate import tracking_target_gate
from project_paths import report_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('snapshot', type=Path)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text())
    nodes = snapshot_target_nodes(snapshot)
    roles = snapshot['tracking_role_tags']
    points = {}
    for role in (0,1,12):
        slot = roles.index(role)
        obj = next(o for o in snapshot['objects'] if o['slot'] == slot)
        address = int(obj['address'],16)
        point = linked_target_position(nodes,address)
        point.update(slot=slot, observed_world_position=obj['matrix'][12:15],
                     max_world_position_error=max(abs(a-b) for a,b in
                         zip(point['position'], obj['matrix'][12:15])))
        points[str(role)] = point
    owned = snapshot['actor_script_context']
    target = owned['tracking_target_observation']
    brain = owned['tracking_brain']
    self_target = target['resolved_actor_address'] == snapshot['actor']['address']
    globals_ = snapshot['tracking_callback_inputs']
    state = snapshot['animation_state']
    phase = next((p for p in state.get('current_action_phases',{}).get('phases',[])
                  if p['index'] == state['phase_index']),None)
    gate = None
    if 'blocked_targets' in globals_ and phase is not None:
        gate = tracking_target_gate(int(target['resolved_actor_address'],16),
                    [int(v,16) for v in globals_['blocked_targets']],phase['flags_byte_23'])
    enabled = gate['target_enabled'] if gate else True
    if enabled and not self_target and brain['tracking_word_618'] & 0x10000:
        raise NotImplementedError('Other target actor role0 is not captured')
    selection = select_tracking_target(brain['tracking_word_618'],
        brain['target_offset_60c'],target['position'],target_enabled=enabled,
        target_is_self=self_target,role0_position=points['0']['position'] if self_target else None)
    arguments = tracking_arguments(brain['base_word_604'],selection['tracking_word'],
        brain['strength_61c'],globals_['delta_time'],globals_['strength_multiplier'],
        target_enabled=enabled)
    result = dict(snapshot=str(args.snapshot),role_points=points,
                  target_selection=selection,arguments=arguments,target_gate=gate,
                  conditional_target_assumption=gate is None,
                  limits=['Linked no-scale branch only; snapshots are unsynchronised.',
                          'Missing gate data implies an enabled-target assumption; gate status is reported explicitly.',
                          'No native callback invocation, final pose or Bevy parity proved.'])
    output=report_path('stage43-tracking-target-hierarchy.json')
    output.write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
