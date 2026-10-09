"""Compare observed actor-owned tracking state; never assert pose parity."""
import argparse
import json
import math
from pathlib import Path

from project_paths import report_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    args = parser.parse_args()
    snapshots = [json.loads(p.read_text()) for p in (args.before, args.after)]
    records = []
    for snapshot in snapshots:
        context = snapshot['actor_script_context']
        records.append(dict(utc=snapshot['utc'],
                            actor_address=context['actor_address'],
                            context_address=context['context_address'],
                            position=snapshot['actor']['world_matrix'][12:15],
                            tracking_brain=context['tracking_brain'],
                            target=context.get('tracking_target_observation')))
    before, after = records
    delta = [y-x for x, y in zip(before['position'], after['position'])]
    result = dict(before_snapshot=str(args.before), after_snapshot=str(args.after),
                  observations=records, position_delta=delta,
                  displacement=math.sqrt(sum(x*x for x in delta)),
                  same_actor=before['actor_address'] == after['actor_address'],
                  same_owned_context=before['context_address'] == after['context_address'],
                  limits=['Unsynchronised snapshots at different times.',
                          'Observed state changes do not prove causality or native pose parity.'])
    output = report_path('stage43-tracking-state-comparison.json')
    output.write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps({'report': str(output), 'displacement': result['displacement'],
                      'same_owned_context': result['same_owned_context']}))


if __name__ == '__main__':
    main()
