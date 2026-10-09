"""Export local rotation poses from already decoded private animation files."""
import json
import hashlib
from jade_pose import rotation_samples
from project_paths import ASSET_ROOT, report_path


def main():
    parts = json.loads(report_path('stage4-sally-all-parts.json').read_text(encoding='utf-8'))
    keys = [obj['key'] for obj in parts['objects']]
    source = ASSET_ROOT / 'animations' / 'sally' / 'local-samples'
    target = ASSET_ROOT / 'animations' / 'sally' / 'local-rotation-poses'
    target.mkdir(parents=True, exist_ok=True)
    rows = []
    maximum_norm_error = 0.0
    for path in sorted(source.glob('*.json')):
        animation = json.loads(path.read_text(encoding='utf-8'))
        pose = rotation_samples(animation, keys)
        pose['source_animation'] = path.stem
        pose['source'] = animation.get('source')
        pose['candidate_object_list'] = '7100AF2A'
        out = target / path.name
        out.write_text(json.dumps(pose, indent=2, allow_nan=False), encoding='utf-8')
        for track in pose['tracks']:
            for sample in track['samples']:
                q = sample['jade_quaternion_xyzw']
                maximum_norm_error = max(maximum_norm_error, abs(sum(v*v for v in q)-1))
        rows.append({'key': path.stem, 'tracks': len(pose['tracks']),
                     'samples': sum(len(t['samples']) for t in pose['tracks']),
                     'unmapped_slots': sorted({t['native_slot'] for t in pose['tracks']
                                                if t['candidate_gao'] is None and not t['native_slot_is_actor_root']}),
                     'output': str(out), 'sha256': hashlib.sha256(out.read_bytes()).hexdigest()})
    result = {'resources': rows, 'max_quaternion_squared_norm_error': maximum_norm_error,
              'limits': pose['limits'] if rows else 'No resources'}
    report_path('stage4-sally-local-poses.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'resources': len(rows), 'rotation_samples': sum(r['samples'] for r in rows),
                      'unmapped_slots': sorted({i for r in rows for i in r['unmapped_slots']})}, indent=2))


if __name__ == '__main__':
    main()
