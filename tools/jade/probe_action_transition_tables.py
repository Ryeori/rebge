"""Compare decoded original action tails with independent native table reads."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from bpak_reader import entries, decode
from jade_scene_probe import PATH
from jade_actions import decode_transition_tables

parser = argparse.ArgumentParser()
parser.add_argument('native', type=Path)
args = parser.parse_args()
source_path = Path('reports/jade/stage4-sally-actions.json')
source = json.loads(source_path.read_text())
actions = {a['key']: a for a in source['actions']}
inventory = {a['name']: a for a in entries(PATH)}
with PATH.open('rb') as archive:
    listing = decode(archive, inventory[source['source_list']])
keys = [f'{struct.unpack_from("<I", listing, i)[0]:08X}' for i in range(0, len(listing), 8)]
decoded = {key: decode_transition_tables(a) for key, a in actions.items()}
checks = []
for action in json.loads(args.native.read_text())['actions']:
    key = keys[action['index']]
    tables = {t['phase']: t for t in decoded[key]['tables']}
    for phase in action['descriptor']['records']:
        native = phase.get('transition_table')
        if native is None:
            continue
        expected = tables[phase['index']]['rows']
        fields = ('requested', 'target', 'flags', 'duration_byte')
        equal = [tuple(r[f] for f in fields) for r in expected] == [tuple(r[f] for f in fields) for r in native['rows']]
        checks.append(dict(action_index=action['index'], key=key, phase=phase['index'],
            count=len(expected), exact=equal, native_stable=native['unchanged']))
        if not equal:
            raise ValueError(f'Native transition table differs: {key} phase{phase["index"]}')
result = dict(source=str(source_path), source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
    native=str(args.native), native_sha256=hashlib.sha256(args.native.read_bytes()).hexdigest(),
    actions=decoded, checks=checks,
    limitations=['Source tail structure confirmed against selected native tables only.',
                 'Transition records do not reveal caller VM predicates.',
                 'Unparsed bytes and unknown header/key words remain explicit.'])
out = Path('reports/jade/stage43-action-transition-decoded-20261009.json')
out.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(dict(output=str(out), decoded_actions=len(decoded),
    native_tables=len(checks), native_rows=sum(c['count'] for c in checks),
    unparsed_actions=sum(bool(a['unparsed_tail_hex']) for a in decoded.values()))))
