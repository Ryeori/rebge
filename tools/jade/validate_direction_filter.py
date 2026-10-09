"""Numerical adjacency check against a narrow native record, not callback proof."""
import argparse
import json
import struct
import math
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('capture', type=Path)
a = p.parse_args()
raw = json.loads(a.capture.read_text())
f32 = lambda x: struct.unpack('<f', struct.pack('<f', x))[0]
vec = lambda h: struct.unpack('<3f', bytes.fromhex(h))
exact, mismatches = [], []
for before, after in zip(raw['rows'], raw['rows'][1:]):
    if not before['unchanged'] or not after['unchanged']:
        continue
    if before['filtered_hex'] == after['filtered_hex']:
        continue
    if before['raw_input_hex'] != after['raw_input_hex'] or before['delta_hex'] != after['delta_hex']:
        continue
    previous = vec(before['filtered_hex'])
    target = vec(after['raw_input_hex'])
    delta = struct.unpack('<f', bytes.fromhex(after['delta_hex']))[0]
    alpha = max(0., min(1., f32(delta * 12.)))
    result = [f32(f32(alpha * x) + f32(f32(1. - alpha) * y)) for x, y in zip(target, previous)]
    predicted = struct.pack('<3f', *result).hex()
    item = dict(before=before['index'], after=after['index'], predicted_hex=predicted,
                observed_hex=after['filtered_hex'], delta=delta)
    (exact if predicted == after['filtered_hex'] else mismatches).append(item)
alignment = []
steering = []
wrap = lambda x: (x + math.pi) % (2 * math.pi) - math.pi
for before, after in zip(raw['rows'], raw['rows'][1:]):
    if not before['unchanged'] or not after['unchanged']:
        continue
    old_world = struct.unpack('<16fI', bytes.fromhex(before['world_hex']))
    new_world = struct.unpack('<16fI', bytes.fromhex(after['world_hex']))
    if old_world[4:7] == new_world[4:7]:
        continue
    delta = struct.unpack('<f', bytes.fromhex(after['delta_hex']))[0]
    target = vec(after['filtered_hex'])
    if not delta or target[0]*target[0]+target[1]*target[1] < 1e-10:
        continue
    old_angle = math.atan2(-old_world[5], -old_world[4])
    new_angle = math.atan2(-new_world[5], -new_world[4])
    desired = wrap(math.atan2(target[1],target[0])-old_angle)
    if abs(desired) > 1e-4:
        steering.append(dict(before=before['index'], after=after['index'], delta=delta,
            desired_angle=desired, observed_angle=wrap(new_angle-old_angle),
            inferred_rate=wrap(new_angle-old_angle)/desired/delta))
for row in raw['rows']:
    if not row['unchanged']:
        continue
    world = struct.unpack('<16fI', bytes.fromhex(row['world_hex']))
    forward = [-x for x in world[4:7]]
    angles = {}
    for name in ['direction_hex', 'filtered_hex', 'raw_input_hex']:
        v = vec(row[name])
        denominator = math.sqrt(sum(x*x for x in forward) * sum(x*x for x in v))
        if denominator:
            dot = sum(x*y for x,y in zip(forward,v))/denominator
            angles[name] = math.acos(max(-1., min(1., dot)))
    if angles:
        alignment.append(dict(index=row['index'], elapsed=row['elapsed'], angles=angles))
report = dict(capture=str(a.capture), exact=exact, mismatches=mismatches, alignment=alignment, steering=steering,
    limitations=['Adjacent changed observations can skip updates.',
                 'Equal read brackets do not establish atomic callback state.'])
output = a.capture.with_name(a.capture.stem + '-filter-validation.json')
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(report=str(output), exact=len(exact), mismatches=len(mismatches))))
