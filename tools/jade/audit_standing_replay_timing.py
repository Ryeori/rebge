"""Compare recorded delivery times with sparse qualified replay observations."""
import argparse
import json
import math
from pathlib import Path
from movement_suite import ROOT


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('fixture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text())
    cases = []
    for case in fixture['cases']:
        run = json.loads(resolve(case['run']).read_text())
        raw = json.loads(resolve(case['source']).read_text())
        origin = run['input_origin_performance_counter']
        commands = [dict(t=e['performance_counter']-origin,
                         norm=math.hypot(e['x'], e['y'])) for e in run['events']]
        observations = case['rows']
        first_input = next(r for r in observations if r['norm'] > 0)
        first_gate = next(r for r in observations if r['norm'] >= .6)
        command_onset = next(r for r in commands if r['norm'] > .35)
        command_gate = next(r for r in commands if r['norm'] >= .6)
        prior_input = [r for r in observations if r['t'] < first_input['t']]
        prior_gate = [r for r in observations if r['t'] < first_gate['t']]
        turn_only = []
        import struct
        for s in raw['samples']:
            turn = s.get('standing_turn_inputs', {})
            t = raw['start_performance_counter'] + s['elapsed_seconds'] - origin
            if t >= 0 and turn.get('unchanged') is True:
                norm = struct.unpack_from('<f', bytes.fromhex(turn['direction_38_norm_74_hex']), 0x3c)[0]
                turn_only.append(dict(t=t, norm=norm, index=s['index']))
        pad_path = next(c['parsed']['report'] for c in run['collectors']
                        if 'probe_gamepad_input.py' in ' '.join(c['command']))
        pad = json.loads(resolve(pad_path).read_text())
        delivered = []
        for sample in pad['winmm_rows']:
            devices = sample['devices']
            if len(devices) != 1:
                continue
            t = pad['start_performance_counter'] + sample['elapsed_seconds'] - origin
            if t < 0:
                continue
            device = devices[0]
            x, y = ((device[k]-32767)/32768 for k in ('x', 'y'))
            delivered.append(dict(t=t, norm=math.hypot(x,y)))
        cases.append(dict(run=case['run'], expected_actions=case['expected_action_sequence'],
            runner_first_input_geometry=run.get('first_input_geometry'),
            sparse_onset_lag_vs_runner_guard_ms=(first_input['t']-run['first_input_geometry']['t'])*1000
                if run.get('first_input_geometry') else None,
            command_first_over_deadzone=command_onset,
            winmm_first_over_deadzone=next((r for r in delivered if r['norm'] > .35), None),
            stable_turn_input_first_nonzero=next((r for r in turn_only if r['norm'] > 0), None),
            qualified_first_nonzero={k:first_input[k] for k in ('t','norm','action','diagnostic_forward_dot')},
            qualified_onset_bracket=[prior_input[-1]['t'] if prior_input else None, first_input['t']],
            sparse_onset_lag_vs_command_ms=(first_input['t']-command_onset['t'])*1000,
            command_first_at_least_06=command_gate,
            winmm_first_at_least_06=next((r for r in delivered if r['norm'] >= .6), None),
            stable_turn_input_first_at_least_06=next((r for r in turn_only if r['norm'] >= .6), None),
            qualified_first_at_least_06={k:first_gate[k] for k in ('t','norm','action','diagnostic_forward_dot')},
            qualified_gate_bracket=[prior_gate[-1]['t'] if prior_gate else None, first_gate['t']],
            sparse_gate_lag_vs_command_ms=(first_gate['t']-command_gate['t'])*1000,
            maximum_qualified_gap_ms=max(b['t']-a['t'] for a,b in zip(observations,observations[1:]))*1000))
    result = dict(schema='standing-replay-timing-audit-v1', cases=cases,
        conclusions=[
            'Holding qualified samples delays input onset and strength updates relative to the external command. This can change accumulated steering before the 0.6/135 degree selection boundary.',
            'Observed lag combines controller quantization, device polling, native callback timing, sequential capture and omitted rejected samples; it is not a measured pure input latency.',
            'A turn result from sparse replay does not by itself refute the native steering formula.',
            'Use run.events recorded performance_counter timestamps for command replay, plus observed WinMM quantized delivery for device-space replay. Preserve independent native world-direction observations.',
            'For camera mapping, interpolate observed world direction only as an explicit approximation; account for source XYZ and native deadzone/normalization. Never interpolate action or actor forward into simulator state.',
            'Bracket unknown publish latency and simulation-frame phase, and evaluate a range of outcomes rather than choosing one fit as parity. If all plausible timings fail, investigate mechanism/caller state; if outcomes straddle the native result, measurement is insufficient.'],
        limits=['Stable turn-input-only rows have weaker qualification than complete pose/selector rows and are used only for input timing.',
                'Runner geometry guard is a separate sequential observation with driver-relative timestamp; it is not callback instrumentation.',
                'WinMM rows have observer wall times, not exact game polling times.',
                'Command norm is before VDS4 quantization and platform normalization; .35 and .6 crossings can differ from game norm.'])
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(cases))


if __name__ == '__main__':
    main()
