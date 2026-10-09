"""Dense external-command replay with explicitly approximate camera mapping."""
import argparse
import bisect
import hashlib
import json
import math
import struct
from pathlib import Path
from movement_suite import ROOT


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def path(x):
    p = Path(x)
    return p if p.is_absolute() else ROOT/p


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def gated_norm(x, y):
    x, y = f32(x), f32(y)
    if abs(x) <= f32(.35) and abs(y) <= f32(.35):
        return 0.
    length = f32(math.sqrt(f32(f32(x*x)+f32(y*y))))
    return 1. if length > f32(.925) else length


def unit(vector):
    length = math.sqrt(sum(v*v for v in vector))
    if length == 0:
        raise ValueError('Zero direction anchor')
    return [f32(v/length) for v in vector]


def interpolate(anchors, t):
    i = bisect.bisect_right([a['t'] for a in anchors], t)
    if i == 0:
        return anchors[0]['direction']
    if i == len(anchors):
        return anchors[-1]['direction']
    a, b = anchors[i-1], anchors[i]
    fraction = (t-a['t'])/(b['t']-a['t'])
    return unit([x+(y-x)*fraction for x,y in zip(a['direction'],b['direction'])])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source_fixture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    observed = json.loads(args.source_fixture.read_text())
    cases = []
    mapping_path = ROOT/'tools/game-automation/python/vgamepad-0.1.0/vgamepad/win/virtual_gamepad.py'
    stick_path = ROOT/'bevy/src/input/stick.rs'
    for case in observed['cases']:
        if not case['case'].startswith('standing_right_rise_'):
            raise ValueError('Only positive X standing right ramps supported')
        run_path = path(case['run'])
        run = json.loads(run_path.read_text())
        if sha(run_path) != case['run_sha256']:
            raise ValueError('Run changed')
        events = run['events']
        if any(e['x'] < 0 or e['y'] != 0 or e['r2'] != 0 for e in events):
            raise ValueError('Unsupported axes or sprint')
        pad_path = path(next(c['parsed']['report'] for c in run['collectors']
                             if 'probe_gamepad_input.py' in ' '.join(c['command'])))
        pad = json.loads(pad_path.read_text())
        delivered = []
        for s in pad['winmm_rows']:
            if len(s['devices']) != 1:
                raise ValueError('Requires single observed WinMM device')
            d = s['devices'][0]
            x, y = [(d[k]-32767)/32768 for k in ('x','y')]
            delivered.append(dict(t=pad['start_performance_counter']+s['elapsed_seconds']-run['input_origin_performance_counter'],
                                  x=x,y=y,norm=gated_norm(x,y)))
        anchors = [dict(t=r['t'], direction=unit(r['direction']))
                   for r in case['rows'] if r['norm'] > 0]
        first = case.get('first_input_geometry')
        if first and first['norm'] > 0:
            anchors.append(dict(t=first['t'],direction=unit(first['direction'])))
        anchors.sort(key=lambda r:r['t'])
        rows = []
        for event in events:
            t = event['performance_counter']-run['input_origin_performance_counter']
            norm = gated_norm(event['x'],event['y'])
            delivery_i = bisect.bisect_right([s['t'] for s in delivered],t)-1
            winmm = delivered[delivery_i] if delivery_i >= 0 else None
            rows.append(dict(t=t, elapsed=event['elapsed'],performance_counter=event['performance_counter'],
                command_x=event['x'],command_y=event['y'],
                ds4_byte_x=128+round(event['x']*127),ds4_byte_y=128+round(event['y']*127),
                norm=norm,direction=interpolate(anchors,t) if norm else [0.,0.,0.],
                latest_observed_winmm=winmm,
                command_minus_latest_winmm_norm=norm-winmm['norm'] if winmm else None))
        cases.append(dict(case=case['case'], run=case['run'],run_sha256=case['run_sha256'],
            source=case['source'],source_sha256=case['source_sha256'],
            pad_source=str(pad_path.relative_to(ROOT)),pad_sha256=sha(pad_path),
            input_origin_performance_counter=run['input_origin_performance_counter'],
            initial_geometry=case['initial_geometry'],initial_right_observation=case['initial_right_observation'],
            duration=case['duration'],expected_action_sequence=case['expected_action_sequence'],
            direction_anchors=anchors,rows=rows,
            independently_observed_rows=case['rows']))
        # Optional independently observed pre-input response. Older recordings
        # lack heading fields; retain that absence rather than fabricate a seed.
        native_source = path(case['source'])
        if sha(native_source) != case['source_sha256']:
            raise ValueError('Native source changed')
        native = json.loads(native_source.read_text())
        before_input = []
        for sample in native['samples']:
            t = native['start_performance_counter'] + sample['elapsed_seconds'] - run['input_origin_performance_counter']
            heading = sample.get('native_heading_inputs', {})
            fields = heading.get('brain_fields_hex', {})
            if (t <= 0 and heading.get('brain_fields_unchanged') is True
                    and heading.get('pointer_identity_unchanged') is True
                    and sample.get('actor_reference_unchanged') is True
                    and '0x1198' in fields):
                before_input.append(dict(index=sample['index'],t=t,
                    value=struct.unpack('<f',bytes.fromhex(fields['0x1198']))[0],
                    raw_hex=fields['0x1198'],brain_fields_unchanged=True,
                    pointer_identity_unchanged=True,actor_reference_unchanged=True))
        if before_input:
            cases[-1]['observed_initial_response1198'] = before_input[-1]['value']
            cases[-1]['initial_response1198_provenance'] = before_input[-1]
    result = dict(schema='native-standing-delivery-replay-v1',
        source_fixture=str(args.source_fixture),source_fixture_sha256=sha(args.source_fixture),
        ds4_mapping_source=str(mapping_path.relative_to(ROOT)),ds4_mapping_sha256=sha(mapping_path),
        global_gate_source=str(stick_path.relative_to(ROOT)),global_gate_sha256=sha(stick_path),
        cases=cases,limits=[
            'norm is modeled Global gate applied to recorded command float, not exact native delivered input. No rescale: component strictly over .35, magnitude strictly over .925 saturates to one.',
            'DS4 report bytes use verified local VDS4 mapping 128+round(value*127). Native platform normalization from bytes remains unresolved.',
            'latest_observed_winmm retains actual quantized observer values and wall times; its norm uses modeled Global gate. Differences include quantization and sample age, not pure quantization error.',
            'World direction uses normalized linear interpolation of qualified native directions and runner first-input geometry. Endpoint extension and interpolation, including future samples, are explicitly approximate camera mapping.',
            'Only positive-X, zero-Y, zero-R2 standing right ramps are supported; arbitrary axis inversion is not inferred.',
            'External event time is publish-call observation, not exact native polling or callback time. Sweep plausible delivery latency and simulation frame phase rather than asserting one replay is parity.',
            'Independent native forward/action/filter rows are expected observations, never simulator state inputs.',
            'Optional initial response1198 is the latest stable pre-input native brain/actor-reference snapshot; sequential checks do not make it an atomic caller-entry state.',
            'Sequential stable native reads do not prove callback chronology or full-pose parity.'])
    args.output.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(output=str(args.output),cases=len(cases),rows=[len(c['rows']) for c in cases])))


if __name__ == '__main__':
    main()
