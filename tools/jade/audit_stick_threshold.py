"""Qualify held-stick probes, retaining delivered axes and native read limits."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from movement_suite import ROOT
from jade_trace_consistency import rejection_reasons

def resolve(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path

def audit(path):
    run = json.loads(path.read_text())
    records = {Path(c['command'][1]).stem: resolve(c['parsed']['report']) for c in run['collectors']}
    trace_path = records['capture_tracking_sequence']
    pad_path = records['probe_gamepad_input']
    trace = json.loads(trace_path.read_text())
    pad = json.loads(pad_path.read_text())
    qualified, rejected, delivered = [], [], []
    for sample in trace['samples']:
        t = trace['start_performance_counter'] + sample['elapsed_seconds'] - run['input_origin_performance_counter']
        if not .25 <= t <= .90:
            continue
        reasons = rejection_reasons(sample)
        writer = sample['speed_writer_inputs']
        if not writer['unchanged']:
            reasons.append('speed_writer_inputs_changed')
        if reasons:
            rejected.append(dict(index=sample['index'], reasons=reasons))
            continue
        qualified.append(dict(t=t, norm=struct.unpack('<f', bytes.fromhex(writer['input_norm_hex']))[0],
                              action=sample['current_action_index_a8']))
    for row in pad['winmm_rows']:
        t = pad['start_performance_counter'] + row['elapsed_seconds'] - run['input_origin_performance_counter']
        if not 0 <= t <= 1.0 or len(row['devices']) != 1:
            continue
        dev = row['devices'][0]
        delivered.append(dict(t=t, x=dev['x'], y=dev['y'],
                              diagnostic_x=(dev['x']-32767)/32768,
                              diagnostic_y=(dev['y']-32767)/32768))
    return dict(case=run['case']['id'], run=str(path),
                sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,trace_path,pad_path]},
                qualified_held=qualified, rejected_held=rejected, delivered_changed_rows=delivered,
                readiness=run.get('readiness'),
                limits=['WinMM normalization is diagnostic, not a recovered native axis formula.',
                        'Sequential reads are stable checks, not atomic callback inputs.',
                        'One repetition per strength does not establish an exact native constant.'])

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('runs', nargs='+', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args=parser.parse_args()
    results=[audit(p) for p in args.runs]
    args.output.write_text(json.dumps(dict(schema='stick-threshold-audit-v1', cases=results), indent=2)+'\n')
    print(json.dumps([dict(case=r['case'], qualified=len(r['qualified_held']),
                           norms=sorted(set(s['norm'] for s in r['qualified_held'])),
                           delivered_peak=max((abs(s['diagnostic_y']) for s in r['delivered_changed_rows']),default=None))
                      for r in results]))
