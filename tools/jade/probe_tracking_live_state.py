"""Compare captured role/phase state against source roles and native gate."""
import argparse
import json

from jade_tracking_phase import tracking_phase_gate
from project_paths import report_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('snapshot')
    args = parser.parse_args()
    with open(args.snapshot, encoding='utf-8-sig') as stream:
        snapshot = json.load(stream)
    source = json.loads(report_path('stage43-sally-tracking-roles.json').read_text())
    tags = snapshot['tracking_role_tags']
    state = snapshot['animation_state']
    phases = state['current_action_phases']['phases']
    index = state['phase_index']
    phase = phases[index] if index < len(phases) else None
    # Captured high byte 1 avoids transition lookup. Other cases need it.
    high = state['component_flags_u16'] >> 8
    if high != 1:
        raise ValueError('Transition phase capture required for this component state')
    result = {
        'snapshot': args.snapshot,
        'role_count': len(tags),
        'all_roles_match_source': tags == source['roles'][:len(tags)],
        'tracking_slots': {str(role): [i for i, tag in enumerate(tags) if tag == role]
                           for role in (0, 1, 12)},
        'captured_counter': state['tracking_counter_byte_af'],
        'gate_byte_b2': state['tracking_gate_byte_b2'],
        'current_phase': phase,
        'phase_gate': tracking_phase_gate(
            state['tracking_counter_byte_af'], 1.0, 0.0,
            current_flags=phase['flags_byte_23'] if phase else None,
            component_high_byte=high,
            phase_control=phase['control_word_24'] if phase else 0),
        'limits': 'Strength/delta are placeholders: this captured allowed phase '
                  'resets the counter independently of them. Unsynchronised snapshot; '
                  'no proof of writer invocation or full pose parity.'}
    report_path('stage43-tracking-live-state.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
