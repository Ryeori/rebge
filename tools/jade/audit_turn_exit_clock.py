"""Read-only independent action80 source-clock audit from recorded native states."""
import argparse
import hashlib
import json
from pathlib import Path
from jade_trace_consistency import rejection_reasons

def audit(source, bank):
    raw = json.loads(source.read_text(encoding='utf-8-sig'))
    template = json.loads(bank.read_text(encoding='utf-8-sig'))
    rows = []
    for sample in raw['samples']:
        if sample['current_action_index_a8'] != 80:
            continue
        reasons = rejection_reasons(sample)
        for key in ('primary_states_unchanged', 'primary_header_unchanged',
                    'primary_phase_descriptor_unchanged'):
            if sample.get(key) is not True:
                reasons.append(key)
        track = sample['primary_clip']['tracks'][1]
        ticks = [frame['tick_raw'] for frame in track['frame_headers']]
        frame = track['frame_index']
        rows.append(dict(index=sample['index'], t=sample['elapsed_seconds'],
            speed=sample['primary_speed_byte'], reasons=reasons,
            primary_block2_hex=sample['primary_header_hex'][4:6],
            descriptor=sample['primary_phase_descriptor']['records'][0],
            clip_address=sample['primary_clip']['resource_address'],
            controlling_track=1, ticks=ticks, frame=frame,
            elapsed=track['elapsed_seconds'],
            source_clock=sum(ticks[:frame])/60+track['elapsed_seconds']))
    qualified = [row for row in rows if not row['reasons']]
    total_ticks = sum(rows[0]['ticks'])
    return dict(schema='native-action80-clock-audit-v1',
        source=str(source), sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        bank=str(bank), bank_sha256=hashlib.sha256(bank.read_bytes()).hexdigest(),
        bank_turn_keys=list(template['controls']['turn']),
        bank_exit_speed=template['controls']['turn']['walk']['speed'],
        total_ticks=total_ticks, source_seconds=total_ticks/60,
        durations_by_speed={str(speed):total_ticks/speed for speed in (56,60,61)},
        qualified=len(qualified), rejected=len(rows)-len(qualified), rows=rows,
        interpretation='Primary runtime byte is60 at binding then56; descriptor64 is a source policy byte, not runtime clock speed. Effective clock delta is speed*dt/60.',
        limits=['Sequential states are not atomic callback reads.',
                'Observed action duration includes callback/sample quantization.',
                'Source clock from controlling track does not prove all pose channels.'])

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('bank',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=audit(args.source,args.bank)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows',)},indent=2))
