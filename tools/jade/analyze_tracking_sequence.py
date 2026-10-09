"""Summarize temporal consistency without treating samples as native frames."""
import argparse
import json
from pathlib import Path
from match_sally_runtime_clip import signature
from project_paths import ASSET_ROOT, report_path
from jade_trace_consistency import rejection_reasons,pair_candidate
from collections import Counter


def summarize(sequence, sources):
    samples = sequence['samples']
    groups = []
    for sample in samples:
        marker = sample['primary_marker_before']
        if not groups or groups[-1]['marker'] != marker:
            groups.append(dict(marker=marker, first_index=sample['index'],
                               first_seconds=sample['elapsed_seconds'], samples=0))
        groups[-1]['samples'] += 1
        groups[-1]['last_seconds'] = sample['elapsed_seconds']
    variants = {}
    for sample in samples:
        sig = signature(sample['primary_clip']['tracks'], True)
        key = json.dumps(sig)
        if key not in variants:
            variants[key] = dict(track_count=sample['primary_clip']['track_count'],
                candidates=[name for name, source in sources if signature(source['tracks']) == sig])
    pose_signatures = lambda sample: tuple(tuple(obj['matrix']) for obj in sample['objects'])
    changing_without_marker = sum(
        a['primary_marker_before'] == b['primary_marker_before'] and
        pose_signatures(a) != pose_signatures(b)
        for a, b in zip(samples, samples[1:]))
    return dict(sample_count=len(samples), duration_seconds=samples[-1]['elapsed_seconds'],
        stable_markers=sum(s['primary_marker_unchanged'] for s in samples),
        stable_instances=sum(s['primary_instance_unchanged'] for s in samples),
        full_state_checks=sum('primary_states_unchanged' in s for s in samples),
        stable_full_states=sum(s.get('primary_states_unchanged', False) for s in samples),
        update_pass_checks=sum('update_pass_unchanged' in s for s in samples),
        stable_update_passes=sum(s.get('update_pass_unchanged',False) for s in samples),
        update_pass_delta=(samples[-1]['update_pass_after']-samples[0]['update_pass_before'])&0xffffffff
                          if all('update_pass_before' in s for s in samples) else None,
        update_pass_crossing_indices=[s['index'] for s in samples
                                     if s.get('update_pass_unchanged') is False],
        distinct_primary_state_arrays=len({s['primary_states_before_hex'] for s in samples
                                           if 'primary_states_before_hex' in s}),
        fully_checked_samples=sum(all(s.get(k,False) for k in (
            'primary_states_unchanged','primary_link_unchanged',
            'primary_resource_unchanged','primary_instance_unchanged',
            'component_prefix_unchanged','update_pass_unchanged',
            'brain_unchanged','target_reference_unchanged')) for s in samples),
        target_reference_checks=sum('target_reference_unchanged' in s for s in samples),
        motion_qualified_samples=sum(not rejection_reasons(s) for s in samples),
        motion_rejection_reasons=dict(Counter(reason for s in samples for reason in rejection_reasons(s))),
        adjacent_pass_candidates=[dict(first=a['index'],second=b['index'],**pair_candidate(a,b))
            for a,b in zip(samples,samples[1:]) if pair_candidate(a,b)['candidate']],
        distinct_targets=sorted({s['target_resolved_address'] for s in samples
                                 if 'target_resolved_address' in s}),
        distinct_instances=len({s['primary_instance_address'] for s in samples}),
        pose_window_ms=dict(minimum=min(s['pose_read_window_ms'] for s in samples),
                            maximum=max(s['pose_read_window_ms'] for s in samples)),
        marker_runs=groups, distinct_world_poses=len({pose_signatures(s) for s in samples}),
        adjacent_pose_changes_without_marker=changing_without_marker,
        actor_positions=[list(p) for p in sorted({tuple(s['actor']['world_matrix'][12:15]) for s in samples})],
        distinct_brain_blocks=len({s['brain_604_61f_hex'] for s in samples}),
        header_variants=list(variants.values()),
        limitations=['No native frame counter: marker changes do not establish consecutive frames.',
                     'Equal markers do not prove atomic reads or callback input order.',
                     'Older captures may lack target/phase/transition data; blocked table and payloads absent in temporal captures.',
                     'Header matches identify candidates only; no payload or final pose parity claim.'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('snapshot', type=Path)
    args = parser.parse_args()
    sources = [(p.stem, json.loads(p.read_text())) for p in
               sorted((ASSET_ROOT/'animations/sally/local-samples').glob('*.json'))]
    result = summarize(json.loads(args.snapshot.read_text()), sources)
    result['snapshot'] = str(args.snapshot)
    output = report_path(args.snapshot.stem+'-analysis.json')
    output.write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
