"""Identify captured reverse-input clips by source signatures, retain qualification."""
import collections
import hashlib
import json
import sys
from pathlib import Path
from project_paths import ASSET_ROOT, PROJECT_ROOT
from match_sally_runtime_clip import signature
from jade_trace_consistency import rejection_reasons

path = Path(sys.argv[1])
trace = json.loads(path.read_text())
sources = [(p.stem, json.loads(p.read_text())) for p in
           sorted((ASSET_ROOT/'animations/sally/local-samples').glob('*.json'))]
source_signatures = [(key, signature(source['tracks'])) for key, source in sources]
events = []
last = None
summary = collections.defaultdict(lambda: dict(samples=0, qualified=0, phases={}))
for sample in trace['samples']:
    action = sample['current_action_index_a8']
    phase = sample['current_phase_index']
    matches = [key for key, sig in source_signatures
               if sig == signature(sample['primary_clip']['tracks'], True)]
    reasons = rejection_reasons(sample)
    status = summary[action]
    status['samples'] += 1
    status['qualified'] += not reasons
    status['phases'][str(phase)] = matches
    current = (action, phase, tuple(matches))
    if current != last:
        events.append(dict(index=sample['index'], elapsed=sample['elapsed_seconds'],
            action=action, phase=phase, source_candidates=matches,
            requested=sample['requested_action_index_aa'],
            phase_descriptor=sample['primary_phase_descriptor'],
            rejection_reasons=reasons))
        last = current
output = path.with_name(path.stem+'-reverse-audit.json')
report = dict(input=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    events=events, actions=dict(summary), limitations=[
        'Reverse input command sequence is external wall time; not callback timing.',
        'Signature match identifies source frames, not complete native pose.',
        'Observed action indices and signatures do not recover VM predicates or semantic names.',
        'Qualification checks sequential consistency, not atomic callback inputs.'])
output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(report=str(output),events=[{k:e[k] for k in
    ('index','action','phase','source_candidates','rejection_reasons')} for e in events],actions=dict(summary))))
