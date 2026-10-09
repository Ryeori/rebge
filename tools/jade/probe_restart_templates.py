"""Find qualified intermediary51 primary templates in selected private captures."""
import argparse
import hashlib
import json
from pathlib import Path
from jade_trace_consistency import rejection_reasons
from match_sally_runtime_clip import signature

parser = argparse.ArgumentParser()
parser.add_argument('sequences', nargs='+', type=Path)
args = parser.parse_args()
keys = ('7100B2E4', '9E0004E6')
clips = {key: json.loads(Path(f'assets/animations/sally/local-samples/{key}.json').read_text()) for key in keys}
result = []
for path in args.sequences:
    data = json.loads(path.read_text())
    matches = {key: [] for key in keys}
    for sample in data['samples']:
        if rejection_reasons(sample):
            continue
        for key, clip in clips.items():
            if signature(sample['primary_clip']['tracks'], True) == signature(clip['tracks']):
                matches[key].append(dict(sample=sample['index'], action=sample.get('current_action_index_a8'), phase=sample['current_phase_index']))
    result.append(dict(source=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),matches=matches))
out = Path('reports/jade/stage43-restart-template-search-20261009.json')
out.write_text(json.dumps(dict(sequences=result,limitations=['Clip signature and qualified read only; not a controller behavior proof.']),indent=2)+'\n')
print(json.dumps(dict(report=str(out),sequences=result)))
