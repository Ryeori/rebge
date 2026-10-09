"""Qualify recorded native turn gates; snapshots do not prove callback order."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from movement_suite import ROOT
from jade_trace_consistency import rejection_reasons

def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]

def audit(path):
    run = json.loads(path.read_text())
    record = next(c['parsed']['report'] for c in run['collectors']
                  if 'capture_tracking_sequence.py' in ' '.join(c['command']))
    source = Path(record)
    if not source.is_absolute():
        source = ROOT / source
    raw = json.loads(source.read_text())
    rows, rejected = [], []
    for s in raw['samples']:
        t = raw['start_performance_counter'] + s['elapsed_seconds'] - run['input_origin_performance_counter']
        if not 0 <= t <= run['case']['duration']:
            continue
        turn = s.get('standing_turn_inputs', {})
        stationary = s.get('stationary_selector_inputs', {})
        reasons = rejection_reasons(s)
        for name, ok in [('turn_inputs', turn.get('unchanged')),
                         ('time_globals', stationary.get('unchanged')),
                         ('actor_reference', s.get('actor_reference_unchanged'))]:
            if ok is not True:
                reasons.append(name)
        if reasons:
            rejected.append(dict(index=s['index'], reasons=reasons))
            continue
        fields = turn['actor_fields_hex']
        def field(offset, fmt):
            return struct.unpack(fmt, bytes.fromhex(fields['0x' + offset]))[0]
        joy = bytes.fromhex(turn['direction_38_norm_74_hex'])
        direction = struct.unpack_from('<3f', joy)
        norm = struct.unpack_from('<f', joy, 0x3c)[0]
        globals_ = stationary['globals_hex']
        times = [struct.unpack('<f', bytes.fromhex(globals_[key]))[0]
                 for key in ('0x1420a3310', '0x14210c174')]
        age = f32(f32(times[0] - times[1]) - field('da8', '<f'))
        matrix = s['actor']['world_matrix']
        actor_flags = struct.unpack_from('<I', bytes.fromhex(s['actor_dispatch_prefix_hex']))[0]
        forward = [-matrix[i] for i in (4,5,6)]
        right = matrix[:3]
        squared = f32(f32(f32(right[1]*right[1])+f32(right[0]*right[0]))+f32(right[2]*right[2]))
        inverse = f32(1. / f32(math.sqrt(squared)))
        right = [f32(value*inverse) for value in right]
        dot = f32(f32(f32(forward[1]*direction[1]) + f32(forward[0]*direction[0]))
                  + f32(forward[2]*direction[2]))
        orientation = s.get('native_orientation_inputs', {})
        direction_filter = s.get('native_direction_filter_inputs', {})
        filter_audit = dict(present=bool(direction_filter), unchanged=direction_filter.get('unchanged'))
        if direction_filter.get('unchanged') is True:
            filter_audit.update(raw=list(struct.unpack('<3f', bytes.fromhex(direction_filter['raw_direction_14_hex']))),
                filtered=list(struct.unpack('<3f', bytes.fromhex(direction_filter['filtered_direction_1e4_hex']))))
        orientation_audit = dict(present=bool(orientation), unchanged=orientation.get('unchanged'))
        if orientation.get('unchanged') is True:
            header = bytes.fromhex(orientation['dynamics_header_hex'])
            block = orientation.get('block_48_hex')
            orientation_audit.update(flags=hex(struct.unpack_from('<I',header)[0]),
                header_hex=orientation['dynamics_header_hex'],block_hex=block,
                block_floats=list(struct.unpack('<5f',bytes.fromhex(block))) if block else None)
        rows.append(dict(index=s['index'], t=t, action=s['current_action_index_a8'],
                         phase=s['current_phase_index'], direction=direction, norm=norm,
                         blend_active=s['selector_inputs']['blend_active'],
                         orientation=orientation_audit,
                         direction_filter=filter_audit,
                         actor_flags=hex(actor_flags), ordinary_forward=not bool(actor_flags & 0x400000),
                         forward=forward, right=right,
                         diagnostic_forward_dot=dot,
                         configured_action=field('2c', '<i'), mode=field('34', '<i'),
                         bypass_cooldown=field('4c0', '<i'), cooldown_age=age,
                         last_action=field('10c4', '<i'), speed=field('10d4', '<f'),
                         pending_action=field('119c', '<i'),
                         scalar_gates_open=norm >= f32(.6) and field('10c4', '<i') not in (26,27)
                         and (field('4c0', '<i') != 0 or age >= .5)))
    events=[]
    for row in rows:
        if not events or events[-1]['action'] != row['action']:
            events.append(row)
    first_input = next((r for r in rows if r['norm'] > 0), None)
    direction_check = dict(status='unavailable')
    if first_input:
        dot = first_input['diagnostic_forward_dot']
        direction_check = dict(status='opposite_candidate' if dot < f32(-.70710677) else 'setup_direction_contaminated',
                               first_input_index=first_input['index'], first_input_t=first_input['t'],
                               diagnostic_forward_dot=dot,
                               limitation='First accepted sample is after input; this is a setup diagnostic, not an atomic initial-angle measurement.')
    return dict(run=str(path), source=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                case=run['case']['id'], direction_check=direction_check,
                qualified=len(rows), rejected=rejected, events=events, rows=rows)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('runs', type=Path, nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args()
    result=dict(schema='native-standing-turn-input-audit-v1', runs=[audit(p) for p in args.runs],
                limits=['Sequential stable snapshots are not atomic callback inputs.',
                        'Forward is derived from observed actor matrix; native helper context pointer identity and dispatch scheduling remain unproven.',
                        'Special actor flag 0x400000 requires another forward path. Scalar gates alone do not predict a turn.'])
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps([dict(case=r['case'], qualified=r['qualified'], rejected=len(r['rejected']),
                           events=[dict(t=e['t'], action=e['action'], norm=e['norm'], age=e['cooldown_age'],
                                        bypass=e['bypass_cooldown'], configured=e['configured_action']) for e in r['events']]) for r in result['runs']], indent=2))

if __name__ == '__main__':
    main()

