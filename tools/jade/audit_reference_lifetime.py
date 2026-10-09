"""Measure reference changes on fixed, qualified adjacent update passes."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from jade_trace_consistency import pair_candidate

BASIS = (0, 1, 2, 4, 5, 6, 8, 9, 10)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sequence', type=Path)
    args = parser.parse_args()
    raw = args.sequence.read_bytes()
    samples = json.loads(raw)['samples']
    cases, skipped = [], []
    for a, b in zip(samples, samples[1:]):
        reasons = pair_candidate(a, b)['reasons']
        pa, pb = (bytes.fromhex(s['component_aa_b5_hex']) for s in (a, b))
        if pa[:3] != pb[:3]:
            reasons.append('controller_phase_changed')
        if a['primary_clip']['resource_address'] != b['primary_clip']['resource_address']:
            reasons.append('resource_changed')
        for s in (a, b):
            if s.get('actor_reference_unchanged') is not True:
                reasons.append('reference_not_stable_during_snapshot')
        if reasons:
            skipped.append(dict(before=a['index'], after=b['index'], reasons=sorted(set(reasons))))
            continue
        old, new = (struct.unpack('<16fI', bytes.fromhex(s['actor_reference_matrix_hex'])) for s in (a, b))
        world = b['actor']['world_matrix']
        cases.append(dict(before=a['index'], after=b['index'], repeat_before=pa[3], repeat_after=pb[3],
            prior_reference=list(old), observed_reference=list(new), observed_world=world,
            basis_change=max(abs(new[i]-old[i]) for i in BASIS),
            position_change=max(abs(new[i]-old[i]) for i in (12, 13, 14)),
            reference_world_basis_error=max(abs(new[i]-world[i]) for i in BASIS)))
    unchanged_repeat = [c for c in cases if c['repeat_before'] == c['repeat_after']]
    summary = dict(qualified_pairs=len(cases), unchanged_repeat_pairs=len(unchanged_repeat),
        unchanged_repeat_basis_changes=sum(c['basis_change'] != 0 for c in unchanged_repeat),
        unchanged_repeat_position_changes=sum(c['position_change'] != 0 for c in unchanged_repeat),
        changed_basis_matching_world=sum(c['basis_change'] != 0 and c['reference_world_basis_error'] == 0
                                        for c in unchanged_repeat))
    result = dict(source_record=str(args.sequence), source_sha256=hashlib.sha256(raw).hexdigest(),
        selection='Adjacent guarded update passes, same actor, phase and resource; no error filtering.',
        summary=summary, cases=cases, skipped=skipped,
        limitations=['Sequential reads are not atomic callback inputs.',
                     'Unchanged repeat does not prove no entry or controller seek occurred.',
                     'Matrix changes do not identify the executing writer.'])
    path = args.sequence.with_name(args.sequence.stem+'-reference-lifetime.json')
    path.write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(report=str(path), **summary)))


if __name__ == '__main__':
    main()
