"""Report missing inputs without promoting nearby samples to native callback input."""
import argparse
import json
from collections import Counter
from pathlib import Path
from jade_trace_consistency import pair_candidate
from project_paths import report_path

REQUIRED=('actor_reference_matrix_hex','actor_reference_unchanged','component_height_b4',
          'tracking_role_tags','tracking_inputs','current_phase_control',
          'tracking_counter_af','tracking_gate_b2')
INPUT_CHECKS=('actor_reference_unchanged','tracking_inputs_unchanged','tracking_roles_unchanged')


def input_rejection_reasons(sample):
    """Presence alone does not establish stable captured tracking inputs."""
    return [key+(':missing' if key not in sample else ':changed')
            for key in INPUT_CHECKS if sample.get(key) is not True]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('snapshot',type=Path)
    args=parser.parse_args();samples=json.loads(args.snapshot.read_text())['samples']
    candidates=[];missing=Counter();unstable=Counter();primary_only=0;clip_switches=0;stable_pairs=0
    for first,second in zip(samples,samples[1:]):
        qualification=pair_candidate(first,second)
        if not qualification['candidate']:continue
        absent=[key for key in REQUIRED if key not in second]
        missing.update(absent)
        input_rejections=input_rejection_reasons(first)+input_rejection_reasons(second)
        unstable.update(set(input_rejections))
        if not absent and not input_rejections:stable_pairs+=1
        same_clip=first['primary_clip']['resource_address']==second['primary_clip']['resource_address']
        active=second['component_flags_u16']>>8&15
        if active==1:primary_only+=1
        if not same_clip:clip_switches+=1
        candidates.append(dict(first=first['index'],second=second['index'],
            missing_inputs=absent,primary_only=active==1,same_primary_resource=same_clip,
            input_rejections=sorted(set(input_rejections)),
            callback_input_proven=False))
    result=dict(snapshot=str(args.snapshot),adjacent_pass_candidates=len(candidates),
        primary_only_candidates=primary_only,primary_resource_switch_pairs=clip_switches,
        missing_input_counts=dict(missing),pairs=candidates,
        stable_tracking_input_pairs=stable_pairs,unstable_input_pair_counts=dict(unstable),
        limitations=['Candidates establish adjacent update-pass samples only, not callback input age.',
                    'No native prior-world or pre-correction local pose inferred from final samples.',
                    'Active-transition phase resolution and other-target role0 still require explicit evidence.'])
    report_path(args.snapshot.stem+'-tracking-input-audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='pairs'}))


if __name__=='__main__':main()
