"""Record the proven loader/consumer chain and bounded transform timelines."""
import hashlib
import json
from jade_animation_time import locate_transform_segment
from project_paths import ASSET_ROOT, report_path


def main():
    parts = json.loads(report_path('stage4-sally-all-parts.json').read_text(encoding='utf-8'))
    keys = [obj['key'] for obj in parts['objects']]
    binding = {'schema': 'jade-indexed-animation-binding-v1', 'actor': '71003F5A',
               'descriptor': '7100AF29', 'object_list': '7100AF2A',
               'object_list_sha256': parts['source_sha256'],
               'native_chain': ['1409ea250:pre-action word2 -> visual+8',
                                '1409bf060:visual+8 ->1409be7b0:param3',
                                '1409be7b0 ->1409ed490 ->153d51380:descriptor',
                                '1409ed200 ->153d2d340:ordered GAO list',
                                '153602b50:clone entries sequentially',
                                '1409be7b0:cloned indexed list ->visual+10',
                                '140b49ba0/140b49fb0:short1 ->indexed list+18[slot*16]'],
               'slots': [{'slot': slot, 'gao_key': key} for slot, key in enumerate(keys)],
               'root_slot': 65535,
               'limits': 'Indexed binding confirmed statically. Clone parent remapping, '
                         'runtime time flags, full animated pose/skinning need separate verification.'}
    target = ASSET_ROOT / 'skeletons' / 'sally' / 'animation-binding.json'
    target.write_text(json.dumps(binding, indent=2), encoding='utf-8')
    resources = []
    for path in sorted((ASSET_ROOT/'animations'/'sally'/'local-samples').glob('*.json')):
        clip = json.loads(path.read_text(encoding='utf-8'))
        rows = []
        for track in clip['tracks']:
            slot = track['short1']
            if slot != 65535 and slot >= len(keys):
                raise ValueError(f'Invalid slot{slot}')
            duration = sum(f['tick_raw'] for f in track['frames'])/60.0
            row = {'track_index': track['index'], 'slot': slot,
                   'gao_key': keys[slot] if slot != 65535 else '71003F5A',
                   'duration_from_ticks': duration, 'source_flags': track['source_flags'],
                   'runtime_mode': 'Unresolved per caller; source flags are not runtime loop flags'}
            try:
                row['hold_mode_probes'] = [{ 'elapsed': t, **locate_transform_segment(track, t)}
                                          for t in (0, duration/2, duration, duration+1/60)]
            except ValueError as error:
                row['unsupported'] = str(error)
            rows.append(row)
        resources.append({'key': path.stem, 'tracks': rows})
    report = {'binding_path': str(target), 'binding_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
              'resources': resources, 'limits': binding['limits']}
    report_path('stage4-sally-animation-binding.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'slots': len(keys), 'resources': len(resources),
                      'tracks': sum(len(r['tracks']) for r in resources),
                      'unsupported': sum('unsupported' in t for r in resources for t in r['tracks'])}))


if __name__ == '__main__':
    main()
