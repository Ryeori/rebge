"""Exercise verified VM prefixes under explicit diagnostic context."""
import json
from collections import Counter
from jade_vm_state import VMState, UnsupportedVM
from project_paths import report_path


def main():
    source = json.loads(report_path('stage4-sally-linked-events.json').read_text())
    rows, stops = [], Counter()
    for track in source['tracks']:
        for frame in track['controls']:
            if not frame.get('linked_records'):
                continue
            state = VMState(context_sentinel=0, objects={})
            row = {'resource_key': track['resource_key'], 'track_index': track['track_index'],
                   'frame_index': frame['frame_index'], 'executed_prefix': 0, 'terminal': False}
            for index, record in enumerate(frame['linked_records']):
                try:
                    if not state.execute(record):
                        row['terminal'] = True
                        break
                    row['executed_prefix'] += 1
                except (UnsupportedVM, ValueError) as error:
                    row['stop_record'] = index
                    row['stop_reason'] = str(error)
                    stops[str(error)] += 1
                    break
            row['stack_at_stop'] = state.stack
            rows.append(row)
    result = {'events': rows, 'stop_reasons': dict(stops),
              'limits': 'Fresh stack per event; chosen context sentinel0, no object snapshot. Only typed literals/context operator; no event timing, waiting or game side effects.'}
    report_path('stage4-sally-vm-prefixes.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'events': len(rows), 'executed_prefix_records': sum(r['executed_prefix'] for r in rows),
                      'terminal_events': sum(r['terminal'] for r in rows), 'stops': dict(stops)}))


if __name__ == '__main__':
    main()
