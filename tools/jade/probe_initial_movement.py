"""Source action-list identities and qualified native initial movement clips."""
import hashlib
import json
import struct
from pathlib import Path
from bpak_reader import entries, decode
from jade_scene_probe import PATH
from jade_trace_consistency import rejection_reasons
from match_sally_runtime_clip import signature

source_path = Path('reports/jade/stage4-sally-actions.json')
source = json.loads(source_path.read_text())
inventory = {a['name']: a for a in entries(PATH)}
with PATH.open('rb') as archive:
    listing = decode(archive, inventory[source['source_list']])
keys = [f'{struct.unpack_from("<I", listing, i)[0]:08X}' for i in range(0, len(listing), 8)]
actions = {a['key']: a for a in source['actions']}
sequence_path = Path('reports/jade/stage43-tracking-sequence-20261009-150304.json')
samples = json.loads(sequence_path.read_text())['samples']
result = []
for index in (0, 1, 4, 51, 123):
    action = actions[keys[index]]
    clips = []
    for record in action['records']:
        key = record['resource_key']
        path = Path(f'assets/animations/sally/local-samples/{key}.json')
        clip = json.loads(path.read_text()) if path.exists() else None
        matching = [s['index'] for s in samples if clip and not rejection_reasons(s)
                    and signature(s['primary_clip']['tracks'], True) == signature(clip['tracks'])]
        clips.append(dict(key=key, source_exists=clip is not None, qualified_samples=matching))
    result.append(dict(index=index, key=keys[index], records=action['records'], clips=clips))
out = Path('reports/jade/stage43-initial-movement-sources-20261009.json')
out.write_text(json.dumps(dict(source=str(source_path), source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
    sequence=str(sequence_path), sequence_sha256=hashlib.sha256(sequence_path.read_bytes()).hexdigest(),
    listing_sha256=hashlib.sha256(listing).hexdigest(), actions=result,
    limitations=['Qualified snapshots prove clip/clock schema, not action request timing.',
                 'Absent native intermediary clips must remain explicit.']), indent=2)+'\n')
print(json.dumps(dict(report=str(out), actions=result)))
