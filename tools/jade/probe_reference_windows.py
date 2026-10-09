"""Numerical diagnostics for all temporary-pointer observations, no error selection."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from jade_actor_reference import refresh_reference


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    raw = args.capture.read_bytes()
    capture = json.loads(raw)
    cases = []
    for index, row in enumerate(capture['rows']):
        if not row['temporary_world_pointer']:
            continue
        root, actor, observed = (struct.unpack('<16fI', bytes.fromhex(row[key])) for key in
            ('current_actor_matrix_hex', 'original_actor_matrix_hex', 'reference_matrix_hex'))
        timing_reasons = []
        if not row['markers_unchanged']:
            timing_reasons.append('markers_changed')
        if row['actor_world_pointer'] != row['actor_world_pointer_after']:
            timing_reasons.append('temporary_pointer_restored_during_read')
        if not row['refresh_scope_candidate']:
            timing_reasons.append('refresh_scope_not_bracketed')
        if not row['reference_matrix_unchanged'] or not row['original_actor_matrix_unchanged']:
            timing_reasons.append('matrix_inputs_changed')
        case = dict(row=index, root=list(root[:16]), root_flags=root[16],
            saved_actor=list(actor[:16]), saved_actor_flags=actor[16],
            observed_reference=list(observed[:16]), observed_flags=observed[16],
            timing_reasons=timing_reasons, accepted_callback_fixture=not timing_reasons)
        try:
            predicted, flags = refresh_reference(root[:16], root[16], actor[:16], actor[16])
            case.update(predicted_reference=predicted, predicted_flags=flags,
                maximum_error=max(abs(x-y) for x, y in zip(predicted, observed[:16])),
                flags_match=flags == observed[16])
        except (ValueError, NotImplementedError) as error:
            case['error'] = str(error)
        cases.append(case)
    summary = dict(temporary_observations=len(cases),
        accepted_callback_fixtures=sum(c['accepted_callback_fixture'] for c in cases),
        numerical_matches=sum(c.get('maximum_error', float('inf')) <= 1e-5 for c in cases))
    result = dict(source_capture=str(args.capture), source_sha256=hashlib.sha256(raw).hexdigest(),
        selection='Every observation with a temporary actor world pointer, independent of numerical error.',
        cases=cases, summary=summary,
        limitations=['Reading a saved stack pointer after restoration can yield residual or reused stack bytes.',
                     'Numerical agreement alone does not establish writer-time inputs or execution identity.'])
    path = args.capture.with_name(args.capture.stem+'-windows.json')
    path.write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(report=str(path), **summary,
        errors=[dict(row=c['row'], error=c.get('maximum_error'), reasons=c['timing_reasons']) for c in cases])))


if __name__ == '__main__':
    main()
