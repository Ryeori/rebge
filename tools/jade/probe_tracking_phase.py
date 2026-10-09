"""Compare observed AF counters to the resolved primary/transition phase gate.

Counter agreement is not proof of writer execution or callback input age.
"""
import argparse
import json
from pathlib import Path
from jade_trace_consistency import pair_candidate
from jade_tracking_phase import tracking_phase_gate
from project_paths import report_path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('snapshot',type=Path)
    args=parser.parse_args();samples=json.loads(args.snapshot.read_text())['samples'];rows=[];skipped=[]
    for first,second in zip(samples,samples[1:]):
        if not pair_candidate(first,second)['candidate']:continue
        active=second['component_flags_u16']>>8&15;transition_flags=None
        if active!=1:
            if not second.get('transition_phase_unchanged'):
                skipped.append(dict(second=second['index'],reason='Transition phase changed/unavailable'));continue
            transition_flags=second['transition_phase']['flags']
        # Strength does not affect this counter comparison; its incoming
        # value and the pose writer are deliberately outside this audit.
        result=tracking_phase_gate(first['tracking_counter_af'],0.5,second['delta_time'],
            current_flags=second['current_phase_flags'],component_high_byte=active,
            transition_flags=transition_flags,phase_control=second['current_phase_control'] or 0)
        rows.append(dict(first=first['index'],second=second['index'],active_slots=active,
            primary_flags=second['current_phase_flags'],transition_flags=transition_flags,
            expected_counter=result['counter'],actual_counter=second['tracking_counter_af'],
            continue_from_phase_gate=result['continue']))
    summary=dict(checked=len(rows),matched=sum(x['expected_counter']==x['actual_counter'] for x in rows),
        transition_checked=sum(x['active_slots']==3 for x in rows),skipped=len(skipped))
    report_path(args.snapshot.stem+'-tracking-phase.json').write_text(json.dumps(dict(summary=summary,rows=rows,
        skipped=skipped,limitations=['AF counter only; strength and writer execution not validated.',
                                  'Adjacent samples are not atomic callback input captures.']),indent=2))
    print(json.dumps(summary))


if __name__=='__main__':main()
