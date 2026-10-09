"""Diagnostic local matrices with explicit partial coverage, no world parity."""
import json
import argparse
from collections import Counter
from jade_animation_sample import sample_clone_local_matrices
from project_paths import ASSET_ROOT, report_path
from jade_pose import rotation_matrix
from jade_clone_pose import initialize_source_clones, assemble_sampled_clone_world


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--neutral-root-diagnostic', action='store_true',
                        help='Explicit identity actor/reference and disabled translation gates; not native runtime state')
    args = parser.parse_args()
    links = json.loads(report_path('stage4-sally-transform-links.json').read_text(encoding='utf-8'))
    objects = sorted((obj for obj in links['objects'] if obj.get('slot') is not None), key=lambda obj: obj['slot'])
    if args.neutral_root_diagnostic:
        objects = initialize_source_clones(objects)
    snapshots, reasons = [], Counter()
    for path in sorted((ASSET_ROOT/'animations'/'sally'/'local-samples').glob('*.json')):
        clip = json.loads(path.read_text(encoding='utf-8'))
        duration = max((sum(f['tick_raw'] for f in t['frames'])/60 for t in clip['tracks']), default=0)
        context = None
        if args.neutral_root_diagnostic:
            context = {'actor_matrix': rotation_matrix([0, 0, 0, 1]),
                       'reference_matrix': rotation_matrix([0, 0, 0, 1]),
                       'reference_flags': 0,
                       'translation_gates': {t['index']: False for t in clip['tracks']}}
        result = sample_clone_local_matrices(clip, objects, duration/2, root_context=context)
        if context is not None:
            result['jade_world_matrices'] = assemble_sampled_clone_world(result)
        reasons.update(row['reason'] for row in result['unsupported_tracks'])
        snapshots.append({'resource_key': path.stem, 'elapsed_seconds': duration/2, **result})
    output = {'schema': 'jade-clone-local-matrix-diagnostic-v1', 'snapshots': snapshots,
              'root_context': 'Explicit neutral diagnostic; identity matrices, gates disabled' if context else 'Unavailable',
              'unsupported_reasons': dict(reasons),
              'limits': 'Source-state attached clone initialization in neutral diagnostic mode. Track order only; '
                        'no action blending, runtime clone initialization, actor/world conversion, '
                        'parent switching, control VM, skinning or Bevy playback parity.'}
    name = 'stage4-sally-attached-world-snapshots.json' if args.neutral_root_diagnostic else 'stage4-sally-local-matrix-snapshots.json'
    report_path(name).write_text(json.dumps(output, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({'resources': len(snapshots),
                      'complete_local_snapshots': sum(s['complete_local_snapshot'] for s in snapshots),
                      'applied_tracks': sum(len(s['applied_tracks']) for s in snapshots),
                      'unsupported_reasons': dict(reasons)}))


if __name__ == '__main__':
    main()
