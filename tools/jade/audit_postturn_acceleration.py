"""Summarize independent native turn exits; wall-time velocity is diagnostic only."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from jade_trace_consistency import rejection_reasons

PROJECT = Path(__file__).resolve().parents[2]


def source_exit_profile():
    path = PROJECT/'assets/animations/sally/local-samples/7100B5E7.json'
    clip = json.loads(path.read_text())
    frames = clip['tracks'][1]['frames']
    elapsed = 0.
    segments = []
    for a, b in zip(frames, frames[1:]):
        seconds = a['tick_raw']/61.
        start = a['transform']['float3_channels'][0]
        end = b['transform']['float3_channels'][0]
        segments.append(dict(start_seconds=elapsed, duration_seconds=seconds,
            source_planar_speed=math.hypot(end[0]-start[0], end[1]-start[1])/seconds))
        elapsed += seconds
    return dict(source=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        track=1, speed_byte=61, total_seconds=elapsed, segments=segments,
        interpretation='Source translation segment slopes, not whole pose or native callback replay.')


def audit(path):
    raw = json.loads(path.read_text(encoding='utf-8-sig'))
    segments = []
    rows = []
    previous = None
    for sample in raw['samples']:
        action = sample['current_action_index_a8']
        phase = sample['current_phase_index']
        key = (action, phase)
        if not segments or key != (segments[-1]['action'], segments[-1]['phase']):
            if segments:
                segments[-1]['next_observed_time'] = sample['elapsed_seconds']
            segments.append(dict(action=action, phase=phase, first_index=sample['index'],
                first_time=sample['elapsed_seconds'], samples=0, qualified=0,
                speed_bytes=[], blend_samples=0))
        segment = segments[-1]
        segment['samples'] += 1
        segment['qualified'] += not rejection_reasons(sample)
        segment['last_index'] = sample['index']
        segment['last_time'] = sample['elapsed_seconds']
        speed = sample['primary_speed_byte']
        if speed not in segment['speed_bytes']:
            segment['speed_bytes'].append(speed)
        selector = sample['selector_inputs']
        segment['blend_samples'] += bool(selector['blend_active'])
        row = dict(index=sample['index'], time=sample['elapsed_seconds'], action=action,
            phase=phase, speed_byte=speed, scalar=selector['selection_value_48'],
            blend=selector['blend_active'], selector_unchanged=selector['unchanged'],
            speed_inputs_unchanged=sample['speed_writer_inputs']['unchanged'],
            header_unchanged=sample['primary_header_unchanged'],
            rejection_reasons=rejection_reasons(sample))
        if previous and sample['actor']['address'] == previous['actor']['address']:
            dt = sample['elapsed_seconds'] - previous['elapsed_seconds']
            if dt > 0:
                a, b = previous['actor']['world_matrix'], sample['actor']['world_matrix']
                row['diagnostic_planar_speed'] = math.hypot(b[12]-a[12], b[13]-a[13])/dt
                row['same_action_pair'] = action == previous['current_action_index_a8']
        rows.append(row)
        previous = sample
    exits = []
    for i, segment in enumerate(segments):
        if segment['action'] != 80:
            continue
        run = segments[i+1] if i+1 < len(segments) else None
        item = dict(exit_segment=segment, next_segment=run)
        if run and run['action'] == 2:
            item['exit_to_run_observed_seconds'] = run['first_time']-segment['first_time']
            start = run['first_index']
            end = run['last_index']
            run_rows = [r for r in rows if start <= r['index'] <= end]
            blend_end = next((r for r in run_rows if not r['blend']), None)
            item['run_blend_end_observed_seconds'] = (
                blend_end['time']-run['first_time'] if blend_end else None)
            for label, selected in [('exit', [r for r in rows if segment['first_index'] <= r['index'] <= segment['last_index']]),
                                    ('run', run_rows)]:
                values = [r['diagnostic_planar_speed'] for r in selected
                    if r.get('same_action_pair') and 'diagnostic_planar_speed' in r]
                item[label+'_diagnostic_speed_summary'] = dict(count=len(values),
                    minimum=min(values) if values else None,
                    maximum=max(values) if values else None,
                    mean=sum(values)/len(values) if values else None)
        exits.append(item)
    allowed = {0, 1, 2, 3, 4, 51, 53, 54, 78, 79, 80, 116, 117, 123, 176}
    unexpected = sorted({s['action'] for s in segments}-allowed)
    input_records = []
    for input_path in (PROJECT/'reports/jade').glob('stage43-auto-start-input-*.json'):
        record = json.loads(input_path.read_text(encoding='utf-8-sig'))
        capture_path = record.get('capture_report')
        if capture_path and Path(capture_path).resolve() == path.resolve():
            input_records.append(dict(path=str(input_path),
                sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),
                parameters=record.get('parameters'), actions=record['actions'],
                capture_complete=record['capture_complete']))
    return dict(source=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        input_records=input_records,
        recording_parameters=raw.get('recording_parameters'), sample_count=len(rows),
        segments=segments, exits=exits, unexpected_actions=unexpected, rows=rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('traces', nargs='+', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    reports = [audit(p) for p in args.traces]
    result = dict(schema='rebge-native-postturn-audit-v1', reports=reports,
        source_exit_profile=source_exit_profile(), limitations=[
        'Sequential reads; stable markers do not prove atomic callback inputs.',
        'Observed segment boundaries are bracketed by sample interval, not exact action times.',
        'Actor velocity uses sample wall time and may mix frames; source units, not metres.',
        'Qualification of source/pose is distinct from selector and speed consistency.',
        'Action allowlist is a terrain contamination screen, not proof of collision-free movement.',
        'Clip signatures require the separate audit_reverse_capture.py report.'])
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(output=str(args.output), scenarios=[dict(source=r['source'],
        actions=[(s['action'],s['phase'],s['qualified']) for s in r['segments']],
        exits=[{k:v for k,v in e.items() if k not in ('exit_segment','next_segment')} for e in r['exits']],
        unexpected_actions=r['unexpected_actions']) for r in reports])))


if __name__ == '__main__':
    main()
