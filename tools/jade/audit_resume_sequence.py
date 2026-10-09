"""Classify saved clock drops and pose failures without fitting snapshot selection."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from project_paths import ASSET_ROOT, report_path
from match_sally_runtime_clip import signature


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sequence', type=Path)
    args = parser.parse_args()
    raw = args.sequence.read_bytes()
    samples = {s['index']: s for s in json.loads(raw)['samples']}
    sources = {}
    for path in sorted((ASSET_ROOT / 'animations/sally/local-samples').glob('*.json')):
        source = json.loads(path.read_text())
        sources.setdefault(json.dumps(signature(source['tracks'])), []).append((path.stem, source))

    def identify(sample, name):
        matches = sources.get(json.dumps(signature(sample[name + '_clip']['tracks'], True)), [])
        if len(matches) != 1:
            raise ValueError('Unique source required')
        return matches[0]

    epochs = json.loads(args.sequence.with_name(args.sequence.stem + '-clip-epochs.json').read_text())
    events = []
    for event in epochs['events']:
        a, b = (samples[event[key]] for key in ('before', 'after'))
        key, source = identify(b, 'primary')
        x, y = a['primary_clip']['tracks'][0], b['primary_clip']['tracks'][0]
        frame = source['tracks'][0]['frames'][x['frame_index']]
        events.append(dict(event, source=key, root_track_flags=x['track_flags'],
            root_frame_flags_source=frame['flags'],
            root_frame_flags_runtime=x['frame_headers'][x['frame_index']]['flags'], root_tick_raw=frame['tick_raw'],
            root_index_before=x['frame_index'], root_index_after=y['frame_index'],
            root_state_flags_before=x['state_flags'], root_state_flags_after=y['state_flags'],
            classification=('repeat_increment_observed' if event['phase_repeat_before'] != event['phase_repeat_after']
                            else 'forward_root_segment_boundary' if y['frame_index'] == x['frame_index'] + 1
                            else 'root_drop_without_repeat_increment'),
            changed_track_indices=[t['track_index'] for t, u in zip(a['primary_clip']['tracks'], b['primary_clip']['tracks'])
                                   if t['frame_index'] != u['frame_index']],
            post_tracks=[dict(track_index=t['track_index'], frame_index=t['frame_index'],
                             elapsed=t['elapsed_seconds'], state_flags=t['state_flags'],
                             frame_headers=t['frame_headers']) for t in b['primary_clip']['tracks']]))
    motion = json.loads(args.sequence.with_name(args.sequence.stem + '-motion-pose.json').read_text())
    failures = []
    for row in motion['rows']:
        if row.get('rotation_error', 0) <= 1e-5:
            continue
        sample = samples[row['sample']]
        contexts = []
        for name in ('primary', 'transition') if row['active_slots'] == 3 else ('primary',):
            key, source = identify(sample, name)
            tracks = []
            for track, state in zip(source['tracks'], sample[name + '_clip']['tracks']):
                if track['short1'] != row['slot']:
                    continue
                frame = track['frames'][state['frame_index']]
                tracks.append(dict(track_index=state['track_index'], frame_index=state['frame_index'],
                    elapsed=state['elapsed_seconds'], state_flags=state['state_flags'],
                    track_flags=state['track_flags'], frame_flags=frame['flags'], tick_raw=frame['tick_raw'],
                    transform_flags=frame.get('transform', {}).get('flags'),
                    next_frame_flags=track['frames'][(state['frame_index'] + 1) % len(track['frames'])]['flags']))
            contexts.append(dict(instance=name, source=key, tracks=tracks))
        failures.append(dict(row, contexts=contexts))
    result = dict(source_record=str(args.sequence), source_sha256=hashlib.sha256(raw).hexdigest(),
        clock_events=events, rotation_failures=failures,
        failure_slots=dict(Counter(r['slot'] for r in failures)),
        limitations=['Classifications describe observed metadata, not native callback identity.',
                     'Existing qualification is retained; sequential reads are not atomic.',
                     'No failure is discarded or reclassified as parity by this audit.'])
    path = report_path(args.sequence.stem + '-resume-audit.json')
    path.write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps(dict(report=str(path), clock_groups=dict(Counter(e['classification'] for e in events)),
                         failure_slots=result['failure_slots'], failure_samples=sorted(set(r['sample'] for r in failures)))))


if __name__ == '__main__':
    main()
