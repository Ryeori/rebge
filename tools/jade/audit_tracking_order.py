"""Classify observed publication changes without claiming callback inputs."""
import argparse
import collections
import json
from pathlib import Path
from project_paths import report_path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('snapshot',type=Path)
    args=parser.parse_args();source=json.loads(args.snapshot.read_text());rows=source['rows']
    events=[];patterns=collections.Counter()
    for index,(first,second) in enumerate(zip(rows,rows[1:])):
        changed=[name for name in first['matrices'] if first['matrices'][name]!=second['matrices'][name]]
        if not changed:continue
        same_pass=(first['pass_before']==first['pass_after']==second['pass_before']==second['pass_after'])
        clip_checked=bool(first.get('primary_clip_unchanged') and second.get('primary_clip_unchanged'))
        same_clip_state=(clip_checked and first['primary_states_hex']==second['primary_states_hex']
                         and first['primary_header_hex']==second['primary_header_hex'])
        kinds={name.rsplit('_',1)[1] for name in changed}
        kind='world_only' if kinds=={'world'} else 'local_only' if kinds=={'local'} else 'mixed'
        patterns[kind]+=1
        events.append(dict(first=index,second=index+1,changed=changed,kind=kind,
            same_pass=same_pass,clip_checked=clip_checked,same_clip_state=same_clip_state))
    summary=dict(observations=len(rows),events=len(events),patterns=dict(patterns),
        checked_same_pass_same_clip_events=sum(x['same_pass'] and x['same_clip_state'] for x in events),
        primary_state_arrays=len({x.get('primary_states_hex') for x in rows}),
        last_matrix_change_seconds=max((rows[x['second']]['elapsed_seconds'] for x in events),default=None))
    result=dict(source=str(args.snapshot),summary=summary,events=events,
        limitations=['Adjacent sequential observations can straddle writes.',
                    'Same pass and clip bytes do not identify actual callback-entry matrices.',
                    'No native pose parity or reconstructed scheduling asserted.'])
    report_path(args.snapshot.stem+'-audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(summary))


if __name__=='__main__':main()
