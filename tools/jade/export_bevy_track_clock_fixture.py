"""Qualified ordinary forward clocks; controller root epochs excluded explicitly."""
import argparse
import hashlib
import json
from pathlib import Path
from jade_trace_consistency import pair_candidate
from project_paths import report_path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('sequence',type=Path);args=parser.parse_args()
    raw=args.sequence.read_bytes();samples=json.loads(raw)['samples'];cases=[];excluded_epochs=[]
    for before,after in zip(samples,samples[1:]):
        if not pair_candidate(before,after)['candidate']:continue
        if before['primary_clip']['resource_address']!=after['primary_clip']['resource_address']:continue
        a,b=before['primary_clip']['tracks'],after['primary_clip']['tracks']
        # Controller reset visible in the separate root clock, not selected by output error.
        if b[0]['elapsed_seconds']<a[0]['elapsed_seconds']:
            excluded_epochs.append([before['index'],after['index']]);continue
        for x,y in zip(a,b):
            if x['indexed_slot']==65535 or any(f['flags']!=128 for f in x['frame_headers']):continue
            state=lambda t:dict(index=t['frame_index'],elapsed=t['elapsed_seconds'],flags=t['state_flags'])
            cases.append(dict(before_index=before['index'],after_index=after['index'],track_index=x['track_index'],
                              track=dict(frames=x['frame_headers'],flags=x['track_flags'],auxiliary_short=x['auxiliary_short_u16']),
                              before=state(x),after=state(y),delta=after['delta_time'],speed=bytes.fromhex(after['primary_header_hex'])[2],
                              actor_root_terminal=bool(int(after['actor']['flags'],16)&2)))
    path=report_path('stage43-bevy-track-clock-native.json')
    path.write_text(json.dumps(dict(source_record=str(args.sequence),source_sha256=hashlib.sha256(raw).hexdigest(),cases=cases,
        excluded_controller_epochs=excluded_epochs,limitations=['Ordinary transform keys only; root/event/controller restarts separate.',
        'Observed global delta scaled by explicit instance speed byte; no callback-entry timing proof.']),indent=2))
    print(json.dumps(dict(report=str(path),cases=len(cases),excluded_epochs=excluded_epochs)))


if __name__=='__main__':main()
