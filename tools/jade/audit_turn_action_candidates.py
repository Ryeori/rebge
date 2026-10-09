"""Inventory source actor rotations; candidates do not prove gameplay selection."""
import hashlib
import json
import math
import struct
from pathlib import Path
from bpak_reader import entries, decode
from jade_scene_probe import PATH

source_path = Path('reports/jade/stage4-sally-actions.json')
source = json.loads(source_path.read_text())
inventory = {e['name']: e for e in entries(PATH)}
with PATH.open('rb') as archive:
    listing = decode(archive, inventory[source['source_list']])
keys = [f'{struct.unpack_from("<I", listing, i)[0]:08X}' for i in range(0, len(listing), 8)]
actions = {a['key']: a for a in source['actions']}
result = []
for index, key in enumerate(keys):
    action = actions.get(key)
    if not action:
        continue
    clips = []
    for record in action['records']:
        path = Path('assets/animations/sally/local-samples') / (record['resource_key']+'.json')
        if not path.exists():
            continue
        clip = json.loads(path.read_text())
        track = clip['tracks'][0]
        frames = track['frames']
        rotations = [f['transform'].get('quaternion_xyzw') for f in frames]
        rotations = [q for q in rotations if q]
        if not rotations:
            continue
        q = rotations[-1]
        angle = math.degrees(2*math.atan2(q[2], q[3]))
        if abs(angle) > 5:
            clips.append(dict(key=record['resource_key'], angle_z_degrees=angle,
                duration=sum(f['tick_raw'] for f in frames)/60,
                source_flags=track.get('source_flags'), record_bytes=record['bytes12_15']))
    if clips:
        result.append(dict(index=index, key=key, clips=clips))
output = Path('reports/jade/stage43-turn-action-candidates-20261009.json')
output.write_text(json.dumps(dict(actions=result, action_index_keys=keys, listing_sha256=hashlib.sha256(listing).hexdigest(),
    source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
    limits=['Track0 terminal Z quaternion angle is a screening heuristic, not proof of slow-turn behavior or VM predicates.']), indent=2)+'\n')
print(json.dumps(result))
