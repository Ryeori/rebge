"""Export independent native observations for offline replay, without game input."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def absolute(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def export(audit_path):
    audit = json.loads(audit_path.read_text())
    output = []
    for observed in audit['runs']:
        run_path = absolute(observed['run'])
        run = json.loads(run_path.read_text())
        source_path = absolute(observed['source'])
        if digest(source_path) != observed['source_sha256']:
            raise ValueError(f'Changed source: {source_path}')
        raw = json.loads(source_path.read_text())
        origin = run['input_origin_performance_counter']
        preceding = []
        for sample in raw['samples']:
            t = raw['start_performance_counter'] + sample['elapsed_seconds'] - origin
            if t <= 0 and sample.get('actor_reference_unchanged') is True:
                preceding.append((t, sample))
        right_observation = None
        if preceding:
            t, sample = preceding[-1]
            right = sample['actor']['world_matrix'][:3]
            magnitude = math.sqrt(sum(x*x for x in right))
            right_observation = dict(t=t, index=sample['index'],
                                     right=[x/magnitude for x in right],
                                     forward=[-sample['actor']['world_matrix'][i] for i in (4,5,6)],
                                     provenance='Latest pre-case stable actor-reference matrix; normalization uses Python arithmetic, not native f32 helper.',
                                     pose_matrices_unchanged=sample.get('pose_matrices_unchanged'))
        rows = []
        for row in observed['rows']:
            rows.append({key: row.get(key) for key in (
                'index', 't', 'norm', 'direction', 'forward', 'right', 'action',
                'phase', 'blend_active', 'direction_filter', 'diagnostic_forward_dot',
                'configured_action', 'mode', 'bypass_cooldown', 'cooldown_age',
                'last_action', 'speed', 'pending_action', 'scalar_gates_open')})
        output.append(dict(
            case=observed['case'], duration=run['case']['duration'],
            run=str(run_path.relative_to(ROOT)), run_sha256=digest(run_path),
            source=str(source_path.relative_to(ROOT)), source_sha256=digest(source_path),
            audit=str(audit_path.relative_to(ROOT)), audit_sha256=digest(audit_path),
            initial_geometry=run.get('initial_turn_geometry'),
            first_input_geometry=run.get('first_input_geometry'),
            initial_right_observation=right_observation,
            expected_action_sequence=[r['action'] for r in observed['events']],
            rejected=observed['rejected'], rows=rows))
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('audits', type=Path, nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cases = []
    for path in args.audits:
        cases.extend(export(path.resolve()))
    result = dict(schema='native-standing-geometry-replay-v1', cases=cases,
        limits=[
            'Rows are independently measured stable sequential snapshots, not atomic callback inputs.',
            'Sample t is input-relative wall time, not native simulation dt.',
            'Hold the last measured direction/norm between samples only as an explicit replay approximation; omitted rejected intervals are not known inputs.',
            'initial_geometry.forward comes from runner before input; initial_right_observation is a separate pre-case matrix read, not the same atomic observation.',
            'direction_filter is independently qualified; absent or unchanged=false filter values remain missing.',
            'pending_action may be stale even in idle and must not be treated as fresh queue evidence.',
            'World vectors are native source XYZ; convert axes consistently when feeding Bevy.',
            'Do not reset the replay actor heading to every measured row when testing integrated steering; row forward is expected evidence, not input.'])
    args.output.write_text(json.dumps(result, separators=(',', ':'))+'\n')
    print(json.dumps(dict(output=str(args.output), cases=len(cases), rows=[len(c['rows']) for c in cases])))


if __name__ == '__main__':
    main()
