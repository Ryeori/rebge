"""Check the native quantized transition clock on qualified adjacent passes."""
import argparse
import json
import struct
from pathlib import Path
from jade_animation_transition import advance_transition
from jade_trace_consistency import pair_candidate
from project_paths import report_path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('snapshot',type=Path)
    args=parser.parse_args();samples=json.loads(args.snapshot.read_text())['samples'];rows=[];skipped=[]
    for first,second in zip(samples,samples[1:]):
        if not pair_candidate(first,second)['candidate']:continue
        if first['component_flags_u16']>>8&15!=3:continue
        if first.get('transition_instance_address')!=second.get('transition_instance_address'):continue
        if first['transition_clip']['resource_address']!=second['transition_clip']['resource_address']:continue
        if first['primary_clip']['resource_address']!=second['primary_clip']['resource_address']:continue
        before=bytes.fromhex(first['transition_header_hex']);after=bytes.fromhex(second['transition_header_hex'])
        if before[0x59]!=after[0x59]:continue
        expected=advance_transition(active=True,duration_byte=before[0x59],
            elapsed_u16=struct.unpack_from('<H',before,0x5a)[0],delta_seconds=second['delta_time'])
        active=second['component_flags_u16']>>8&15==3
        actual_counter=struct.unpack_from('<H',after,0x5a)[0]
        actual_ratio=second['transition_clip']['tracks'][0]['auxiliary_f32']
        rows.append(dict(first=first['index'],second=second['index'],duration_byte=before[0x59],
            expected=expected,actual_active=active,actual_counter=actual_counter,
            actual_ratio=actual_ratio,active_matched=expected['active']==active,
            counter_matched=expected['elapsed_u16']==actual_counter,
            ratio_error=(abs(expected['downstream_ratio']-actual_ratio) if expected['active'] and active else None)))
    errors=[x['ratio_error'] for x in rows if x['ratio_error'] is not None]
    summary=dict(checked=len(rows),active_matches=sum(x['active_matched'] for x in rows),
        counter_matches=sum(x['counter_matched'] for x in rows),ratio_checked=len(errors),
        ratio_matches=sum(x<=1e-7 for x in errors),maximum_ratio_error=max(errors,default=None))
    report_path(args.snapshot.stem+'-transition-clock.json').write_text(json.dumps(dict(summary=summary,rows=rows,
        limitations=['Uses captured global delta, not proven native call argument.',
                    'Adjacent pass counters do not establish callback-entry atomicity.']),indent=2))
    print(json.dumps(summary))


if __name__=='__main__':main()
