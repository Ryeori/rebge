"""Classify every reference change without fitting or inferring callback inputs."""
import argparse
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    raw = args.capture.read_bytes()
    capture = json.loads(raw)
    rows = capture['rows']
    u32 = lambda value: struct.unpack('<I', bytes.fromhex(value))[0]
    matrix = lambda value: struct.unpack('<16fI', bytes.fromhex(value))
    basis = (0, 1, 2, 4, 5, 6, 8, 9, 10)
    events = []
    for index, (a, b) in enumerate(zip(rows, rows[1:])):
        if a['reference_matrix_hex'] == b['reference_matrix_hex']:
            continue
        same_scope = (a['markers_unchanged'] and b['markers_unchanged']
                      and a['markers_after_hex'] == b['markers_before_hex'])
        matrix_guards_present = all('reference_matrix_unchanged' in row for row in (a, b))
        matrices_stable = matrix_guards_present and all(
            row['reference_matrix_unchanged'] and row['original_actor_matrix_unchanged'] for row in (a, b))
        vm = u32(b['markers_before_hex'][4])
        classification = ('bracketed_vm_pass' if same_scope and vm == 1 else
                          'bracketed_outside_vm_pass' if same_scope and vm == 0 else
                          'scope_changed_or_unstable')
        old, new = (matrix(row['reference_matrix_hex']) for row in (a, b))
        world = matrix(b['original_actor_matrix_hex'])
        events.append(dict(before_row=index, after_row=index+1,
            classification=classification,
            matrix_guards_present=matrix_guards_present, matrices_stable=matrices_stable,
            update_pass=u32(b['markers_before_hex'][0]),
            elapsed_seconds=b['elapsed_seconds'],
            before_markers=a['markers_after_hex'], after_markers=b['markers_before_hex'],
            prior_reference=list(old), observed_reference=list(new), observed_original_actor=list(world),
            basis_change=max(abs(old[i]-new[i]) for i in basis),
            position_change=max(abs(old[i]-new[i]) for i in (12, 13, 14)),
            reference_world_basis_error=max(abs(new[i]-world[i]) for i in basis)))
    summary = dict(observations=len(rows), iterations=capture['iterations'],
        observed_seconds=rows[-1]['elapsed_seconds'] if rows else 0,
        stable_marker_observations=sum(r['markers_unchanged'] for r in rows),
        entry_gate_zero_observations=sum(u32(r['markers_before_hex'][1]) == 0 for r in rows),
        temporary_pointer_observations=sum(r['temporary_world_pointer'] for r in rows),
        refresh_scope_candidates=sum(r['refresh_scope_candidate'] for r in rows),
        reference_changes=len(events), classifications=dict(Counter(e['classification'] for e in events)))
    result = dict(source_capture=str(args.capture), source_sha256=hashlib.sha256(raw).hexdigest(),
        summary=summary, events=events,
        limitations=['Bracketing uses sequential markers, not atomic writes or unique writer identity.',
                     'Animation context can remain stale during the VM pass.',
                     'Duration and iteration limits differ; the recorded time is authoritative.',
                     'Older records lack repeated matrix guards and current VM actor context.'])
    path = args.capture.with_name(args.capture.stem+'-audit.json')
    path.write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(report=str(path), **summary)))


if __name__ == '__main__':
    main()
