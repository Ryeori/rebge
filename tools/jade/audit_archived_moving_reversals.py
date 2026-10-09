"""Read archived no-Shift keyboard reversals and a sprint control; no game I/O."""
import hashlib
import json
import struct
from pathlib import Path
from movement_suite import ROOT
from jade_trace_consistency import rejection_reasons

PAIRS = [('171049','171056'),('171801','171809'),('181658','181708'),
         ('201321','201330'),('201443','201452'),('201857','201905'),
         ('210614','210624')]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    cases=[]
    for input_stamp, trace_stamp in PAIRS:
        input_path=ROOT/f'reports/jade/stage43-auto-start-input-20261009-{input_stamp}.json'
        trace_path=ROOT/f'reports/jade/stage43-tracking-sequence-20261009-{trace_stamp}.json'
        audit_path=trace_path.with_name(trace_path.stem+'-reverse-audit.json')
        controls=json.loads(input_path.read_text())
        trace=json.loads(trace_path.read_text())
        audit=json.loads(audit_path.read_text())
        rows=[]
        events=[]
        rejected=0
        for s in trace['samples']:
            if rejection_reasons(s):
                rejected+=1
                continue
            selector=s.get('selector_inputs',{})
            stationary=s.get('stationary_selector_inputs',{})
            fields=bytes.fromhex(selector.get('state_10c4_hex',''))
            row=dict(t=s['elapsed_seconds'],action=s['current_action_index_a8'],
                phase=s['current_phase_index'], speed_byte=s['primary_speed_byte'],
                mode=stationary.get('mode_34'), mode_stable=stationary.get('unchanged'),
                last_action=stationary.get('last_action_10c4'),
                selection_scalar_48=selector.get('selection_value_48'),
                selector_stable=selector.get('unchanged'),
                speed_10d4=struct.unpack_from('<f',fields,0x10)[0] if len(fields)>=20 else None,
                global_norm=None,
                sources=s.get('primary_clip'))
            rows.append(row)
            state=(row['action'],row['phase'])
            if not events or state!=(events[-1]['action'],events[-1]['phase']):
                events.append({k:row[k] for k in ('t','action','phase')})
        turn=next((r for r in rows if r['action']==79 and r['selector_stable'] is True
                   and r['mode_stable'] is True),None)
        preturn=[r for r in rows if turn and r['t']<turn['t']]
        commands=controls['actions']
        wdown=next((c['at'] for c in commands if c['command']=='W down'),None)
        sdown=next((c['at'] for c in commands if c['command'].startswith('S down')),None)
        sup=next((c['at'] for c in commands if c['command']=='S up'),None)
        walk_before=[r for r in preturn if r['action']==3]
        cases.append(dict(input=str(input_path.relative_to(ROOT)),input_sha256=sha(input_path),
            trace=str(trace_path.relative_to(ROOT)),trace_sha256=sha(trace_path),
            old_audit_source_sha256_matches=sha(trace_path)==audit['sha256'],
            shift_command_present=any('Shift' in c['command'] for c in controls['actions']),
            controls=controls['actions'], qualified=len(rows),rejected=rejected,
            command_walk_before_opposite_seconds=sdown-wdown if sdown is not None and wdown is not None else None,
            command_opposite_hold_seconds=sup-sdown if sdown is not None and sup is not None else None,
            qualified_walk_before_turn_interval=[walk_before[0]['t'],walk_before[-1]['t']] if walk_before else None,
            qualified_events=events,
            qualified_preturn=preturn[-1] if preturn else None,
            first_qualified_turn=turn,
            configured_reverse_hold=controls.get('parameters',{}).get('reverse_hold'),
            configured_run_reverse_after=controls.get('parameters',{}).get('run_reverse_after')))
    output=ROOT/'reports/jade/movement-suite/archived-moving-reversal-audit-20261010.json'
    result=dict(schema='archived-moving-reversal-audit-v1',cases=cases,
        conclusions=[
            'Archived keyboard W to S controls without Shift include action3 to79A/B reversals. Running action2 and Shift are not required for every observed action79 entry.',
            'Both release exit78 and held-input exit80 are represented; release timing must be considered before comparing continuation.',
            'Catalog movement_cases.json contains run_reverse cases with R2=1 but no dedicated steady walking reverse case.',
            'Action79 is a shared observed branch; this does not prove identical walking/sprint acceleration, steering or all poses.'],
        limits=[
            'These older observers do not contain standing_turn_inputs/global norm or filtered direction inputs. selection_scalar_48 is smoothed actor scalar, not native global norm.',
            'speed_10d4 is decoded from stable selector state10c4+0x10; mode qualification is separate.',
            'External command at and trace elapsed have different origins; no exact latency mapping is inferred.',
            'Some traces include standing-turn initial orientation or later re-presses; inspect full action chain and controls.',
            'Historical terrain qualification is not established by this archive-only review.'],
        next_bounded_test_if_needed='One full-strength no-R2 steady-walk reversal: walk forward until qualified action3 and speed10D4 stable, switch opposite without neutral gap, hold through79/80 and stable3, release. Use new observer norm, world/filtered direction, mode34, speed10D4, selector/blend, and geometry guard; require prepared open field. Compare with a separately authorized R2 control only if parameters remain unresolved.')
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(output=str(output),cases=[dict(trace=c['trace'],shift=c['shift_command_present'],
        sequence=[(e['action'],e['phase']) for e in c['qualified_events']],
        turn={k:c['first_qualified_turn'][k] for k in ('mode','last_action','selection_scalar_48','speed_10d4')}
             if c['first_qualified_turn'] else None) for c in cases])))


if __name__=='__main__':
    main()
