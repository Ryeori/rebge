"""Measured same-phase root clocks; selection uses metadata, never output error."""
import argparse
import hashlib
import json
from pathlib import Path
from jade_trace_consistency import pair_candidate
from project_paths import report_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sequence', type=Path)
    args = parser.parse_args()
    raw = args.sequence.read_bytes()
    samples = json.loads(raw)['samples']
    cases, skipped = [], []
    for a, b in zip(samples, samples[1:]):
        reasons = pair_candidate(a, b)['reasons']
        if a['primary_clip']['resource_address'] != b['primary_clip']['resource_address']:
            reasons.append('resource_changed')
        pa, pb = (bytes.fromhex(s['component_aa_b5_hex']) for s in (a, b))
        if pa[:3] != pb[:3] or pa[4] or pb[4]:
            reasons.append('phase/action_changed_or_delta_override')
        if bytes.fromhex(a['primary_header_hex'])[2] != bytes.fromhex(b['primary_header_hex'])[2]:
            reasons.append('speed_changed')
        x, y = a['primary_clip']['tracks'][0], b['primary_clip']['tracks'][0]
        if x['actor_address'] != '0x0' or x['indexed_slot'] != 65535 or not x['track_flags'] & 0x8000:
            reasons.append('different_root_dispatch')
        if any(f['flags'] & 0x7c0 != 0x80 for f in x['frame_headers']):
            reasons.append('nontransform_key')
        if reasons:
            skipped.append(dict(before=a['index'], after=b['index'], reasons=sorted(set(reasons))))
            continue
        state = lambda t: dict(index=t['frame_index'], elapsed=t['elapsed_seconds'], flags=t['state_flags'])
        cases.append(dict(before_sample=a['index'], after_sample=b['index'],
            track=dict(frames=x['frame_headers'], flags=x['track_flags'], auxiliary_short=x['auxiliary_short_u16']),
            before=state(x), after=state(y), delta=b['delta_time'],
            speed=bytes.fromhex(b['primary_header_hex'])[2], repeat_before=pa[3], repeat_after=pb[3],
            phase_repeat_limit=(a['primary_phase_descriptor']['records'][pa[2]]['repeat_limit']
                                if a.get('primary_phase_descriptor',{}).get('present') else None)))
    path = report_path(args.sequence.stem + '-root-clock-native.json')
    path.write_text(json.dumps(dict(source_record=str(args.sequence), source_sha256=hashlib.sha256(raw).hexdigest(),
        cases=cases, skipped=skipped, limitations=['Same-phase observed clock transitions only; older records lack repeat limit.',
        'Reference entry/publish side effects are not measured by this fixture.',
        'Sequential reads, not atomic callback-entry inputs.']), indent=2))
    print(json.dumps(dict(report=str(path), cases=len(cases), skipped=len(skipped))))


if __name__ == '__main__':
    main()
