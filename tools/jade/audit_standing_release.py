"""Associate standing-turn traces with external release times and input markers."""
import argparse
import hashlib
import json
from pathlib import Path
from jade_trace_consistency import rejection_reasons

p = argparse.ArgumentParser()
p.add_argument('trace', type=Path)
p.add_argument('input', type=Path)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
trace = json.loads(a.trace.read_text())
inputs = json.loads(a.input.read_text())
samples = trace['samples']
cases = []
for i, s in enumerate(samples):
    action = s['current_action_index_a8']
    if action not in (116,117) or (i and samples[i-1]['current_action_index_a8']==action):
        continue
    end = next((j for j in range(i+1,len(samples)) if samples[j]['current_action_index_a8']!=action),None)
    if end is None:
        continue
    absolute = trace['start_performance_counter']+s['elapsed_seconds']
    release = next((e for e in inputs['events'] if e['command'].endswith(' up')
                    and e['performance_counter']>absolute),None)
    qualified = [j for j in range(i,end) if not rejection_reasons(samples[j])]
    released = [j for j in qualified if release and
                trace['start_performance_counter']+samples[j]['elapsed_seconds']>release['performance_counter']]
    zero = [j for j in released if samples[j].get('speed_writer_inputs',{}).get('unchanged')
            and samples[j]['speed_writer_inputs'].get('input_norm_hex')=='00000000']
    cases.append(dict(action=action,entry=i,exit=end,next_action=samples[end]['current_action_index_a8'],
        duration=samples[end]['elapsed_seconds']-s['elapsed_seconds'],entry_rejections=rejection_reasons(s),
        qualified_samples=qualified,qualified_after_external_release=released,
        qualified_zero_norm_after_release=zero,
        release_to_exit=trace['start_performance_counter']+samples[end]['elapsed_seconds']-release['performance_counter']
            if release else None))
report=dict(trace=str(a.trace),trace_sha256=hashlib.sha256(a.trace.read_bytes()).hexdigest(),
    input=str(a.input),input_sha256=hashlib.sha256(a.input.read_bytes()).hexdigest(),cases=cases,
    limits=['External commands and sequential reads do not prove atomic callback order.',
            'Source qualification and input unchanged markers are checked separately.',
            'Completion scheduling is a bounded preview policy; native VM predicate is unresolved.'])
a.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(output=str(a.output),cases=[{k:v for k,v in c.items() if not isinstance(v,list)}
    | dict(zero_norm_samples=len(c['qualified_zero_norm_after_release'])) for c in cases])))
