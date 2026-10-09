"""Offline heading sensitivity diagnostic; not native playback/parity validation."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def mul(a, b):
    return f32(f32(a) * f32(b))


def add(a, b):
    return f32(f32(a) + f32(b))


def dot(a, b):
    return add(add(mul(a[1], b[1]), mul(a[0], b[0])), mul(a[2], b[2]))


def joy_norm(previous, target, dt):
    # Finite ordinary scalar branch, animation_selector.rs joy_norm;
    # callback order/mode are assumed, never inferred from this diagnostic.
    if target == 0:
        return 0.0
    rate = struct.unpack('<f', bytes.fromhex('66663640'))[0]
    if previous <= target:
        result = add(mul(dt, rate), previous)
        return target if result > target else max(f32(.35), result)
    result = f32(previous - mul(dt, rate))
    return f32(1) if result > 1 else target if result < target else result


def at_time(rows, t):
    current = None
    for row in rows:
        if row['t'] > t:
            break
        current = row
    return current or {'norm': 0, 'direction': [0, 0, 0]}


def angle_error(current, target):
    return f32((math.atan2(target[1], target[0]) - current + math.pi)
               % math.tau - math.pi)


def model(case, name, previous_response, latency, dt=1 / 60, wall_dt=1 / 60):
    dt = f32(dt)
    forward = case['initial_geometry']['forward']
    heading = math.atan2(forward[1], forward[0])
    filtered = [f32(0)] * 3
    response, scalar = f32(previous_response), f32(0)
    gate = next((row for row in case['rows'] if row['norm'] >= f32(.6)), None)
    if gate is None:
        return {'error': 'No dense command magnitude >= .6'}
    frames = []
    # Stop before source turn playback: this only models ordinary rotation
    # through the first magnitude threshold. Input callback age is swept.
    count = math.floor(gate['t'] / wall_dt)
    for frame in range(count + 1):
        t = frame * wall_dt
        incoming = at_time(case['rows'], t - latency)
        norm = f32(incoming['norm'])
        direction = [f32(x) for x in incoming['direction']]
        alpha = max(0, min(1, mul(dt, 12)))
        filtered = [add(mul(alpha, mul(norm, direction[i])),
                        mul(f32(1 - alpha), filtered[i])) for i in range(3)]
        scalar = joy_norm(scalar, norm, dt)
        yaw = f32(0)
        if scalar > f32(.35) and dot(filtered, filtered) > f32(1e-8):
            error = angle_error(heading, filtered)
            if name == 'mode1':
                response_alpha = max(0, min(1, mul(dt, 5)))
                response = add(mul(f32(1 - response_alpha), response),
                               mul(response_alpha, 1))
                sign = -1 if error < 0 else 1
                angle_part = mul(mul(sign, min(abs(error), f32(norm / f32(3.5)))), .9)
                yaw = mul(angle_part, mul(mul(dt, 30), response))
            else:
                yaw = max(-mul(7.714286, dt), min(mul(7.714286, dt),
                          mul(error, min(mul(dt, 8.1), 1))))
            heading = f32(heading + yaw)
        frames.append({'t': t, 'heading_radians': heading, 'norm': norm,
                       'scalar48_model': scalar, 'response1198_model': response,
                       'yaw': yaw, 'filtered_direction': filtered[:]})
    direction = gate['direction']
    predicted_forward = [f32(math.cos(heading)), f32(math.sin(heading)), 0]
    predicted_dot = dot(predicted_forward, direction)
    observations = case['independently_observed_rows']
    observed = min(observations, key=lambda row: abs(row['t'] - gate['t']))
    observed_dot = dot(observed['forward'], observed['direction'])
    return {'model': name, 'initial_response1198': previous_response,
            'steering_callback_age_seconds': latency, 'dt_seconds': dt,
            'wall_step_seconds': wall_dt,
            'first_command_norm06_t': gate['t'], 'last_integrated_t': frames[-1]['t'],
            'candidate_dot': predicted_dot,
            'candidate_angle_degrees': math.degrees(math.acos(max(-1, min(1, predicted_dot)))),
            'geometry_gate_open': predicted_dot < f32(-.70710677),
            'observed_nearest': {'t': observed['t'], 'norm': observed['norm'],
                                 'action': observed['action'], 'dot': observed_dot,
                                 'angle_degrees': math.degrees(math.acos(max(-1, min(1, observed_dot))))},
            'frames': frames}


def initial_response(case, project):
    source = project / case['source']
    raw_bytes = source.read_bytes()
    if hashlib.sha256(raw_bytes).hexdigest() != case['source_sha256']:
        raise ValueError('Native source hash changed')
    raw = json.loads(raw_bytes)
    origin = case['input_origin_performance_counter']
    candidates = []
    for sample in raw['samples']:
        t = raw['start_performance_counter'] + sample['elapsed_seconds'] - origin
        heading = sample.get('native_heading_inputs', {})
        if (t <= 0 and heading.get('brain_fields_unchanged') is True
                and heading.get('pointer_identity_unchanged') is True):
            fields = heading.get('brain_fields_hex', {})
            if '0x1198' in fields:
                candidates.append({'t': t, 'index': sample['index'],
                                   'value': struct.unpack('<f', bytes.fromhex(fields['0x1198']))[0],
                                   'dt': struct.unpack('<f', bytes.fromhex(heading['dt_1420a3318_hex']))[0]})
    if not candidates:
        raise ValueError('No stable pre-input response1198')
    return candidates[-1]


def main():
    project = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=project / 'reports/jade/movement-suite/native-standing-delivery-replay-20261010.json')
    parser.add_argument('--output', type=Path, default=project / 'reports/jade/movement-suite/heading-replay-model-diagnostic-20261010.json')
    parser.add_argument('--simulation-dt', type=float, nargs='+', default=[1 / 60])
    parser.add_argument('--observed-response', action='store_true',
                        help='Use last stable pre-input1198 from each native source instead of sensitivity assumptions')
    args = parser.parse_args()
    raw = args.input.read_bytes()
    fixture = json.loads(raw)
    results = []
    for case in fixture['cases']:
        response_observation = initial_response(case, project) if args.observed_response else None
        responses = [response_observation['value']] if response_observation else [.84, 1.]
        runs = [model(case, name, response, latency, dt)
                for name in ('mode1', 'old_approx') for response in responses
                for latency in (0., .010, .020) for dt in args.simulation_dt]
        results.append({'case': case['case'], 'source': case['source'],
                        'source_sha256': case['source_sha256'],
                        'initial_response_observation': response_observation,
                        'native_expected_actions': case['expected_action_sequence'], 'models': runs})
        concise = [{'model': r['model'], 'response': r['initial_response1198'],
                    'callback_age_ms': r['steering_callback_age_seconds'] * 1000,
                    'simulation_dt': r['dt_seconds'],
                    'candidate_angle_deg': round(r['candidate_angle_degrees'], 2),
                    'gate_open': r['geometry_gate_open']} for r in runs]
        print(json.dumps({'case': case['case'], 'source': case['source'], 'models': concise}))
    report = {'schema': 'offline-heading-model-sensitivity-v1',
              'fixture': str(args.input), 'fixture_sha256': hashlib.sha256(raw).hexdigest(),
              'limits': ['Diagnostic only; no source clips, animation blends, pending turn freeze or native callback chronology simulated.',
                         'Dense command norm and interpolated world direction are approximate delivery, not native polling observations.',
                         '60Hz wall updates and chosen simulation dt are model assumptions; scalar48 finite ordinary callback uses strict >.35 caller gate; mode/caller chronology is not reconstructed.',
                         'Observed1198 mode uses last stable pre-input brain snapshot, not atomic entry state; otherwise .84/1 are sensitivity assumptions.',
                         'Latency sweep delays steering/filter/scalar inputs relative to instantaneous raw norm turn gate.',
                         'Nearest stable observed angle can occur at a different magnitude/time and can already include native queue freeze.',
                         'Mode1 norm operand dereferences pointer142156a70 in listing14110d77b; static context and newer runtime identity confirm Global raw norm, earlier traces omit that identity observation.',
                         'No response/heading is reset to measured rows after initialization; outputs are model predictions, not parity assertions.'],
              'cases': results}
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(str(args.output))


if __name__ == '__main__':
    main()
