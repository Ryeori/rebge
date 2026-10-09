"""Audit short walking reversals from case-relative observations; no game I/O."""
import argparse
import hashlib
import json
from pathlib import Path
from audit_standing_turn_inputs import audit


def compact(row):
    if row is None:
        return None
    return {k:row[k] for k in ('index','t','action','phase','norm','speed','mode',
        'last_action','blend_active','diagnostic_forward_dot','configured_action',
        'bypass_cooldown','cooldown_age','pending_action','forward','direction')}


def analyze(path):
    run=json.loads(path.read_text())
    result=audit(path)
    rows=result['rows']
    command=next(e for e in run['events'] if e['x']>.6)
    command_t=command['performance_counter']-run['input_origin_performance_counter']
    initial_input=next(r for r in rows if r['norm']>0)
    initial_direction=initial_input['direction']
    opposite=next((r for r in rows if r['t']>=command_t and r['norm']>=.6
                   and sum(a*b for a,b in zip(r['direction'],initial_direction))<-.7),None)
    pre=next((r for r in reversed(rows) if r['t']<command_t),None)
    candidates=[]
    for r in rows:
        if r['t']<command_t or not r['scalar_gates_open'] or r['diagnostic_forward_dot']>=-.70710677:
            continue
        candidates.append(dict(**compact(r),gate_speed_selects79=r['mode']<5 and r['speed']>2.5))
    events=[]
    for row in rows:
        if not events or (row['action'],row['phase'])!=(events[-1]['action'],events[-1]['phase']):
            events.append(compact(row))
    return dict(case=run['case']['id'],run=str(path),run_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        source=result['source'],source_sha256=result['source_sha256'],qualified=result['qualified'],
        rejected=result['rejected'],command_opposite=command,command_opposite_t=command_t,
        initial_case_input=compact(initial_input),last_qualified_before_command=compact(pre),
        first_qualified_opposite=compact(opposite),qualified_events=events,
        first_open_angle_scalar_gate=candidates[0] if candidates else None,
        gate_candidate_rows=candidates,
        outcome79=any(r['action']==79 for r in rows),
        outcome116_or117=any(r['action'] in (116,117) and r['t']>=command_t for r in rows))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('runs',type=Path,nargs='+')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    cases=[analyze(path) for path in args.runs]
    result=dict(schema='native-short-walking-reversal-audit-v1',cases=cases,
        limits=['Only input-relative case samples are used; pre-case setup motion is excluded.',
            'Complete pose/selector/input qualification uses audit_standing_turn_inputs; rejected rows remain recorded.',
            'First qualified opposite sample is a sampled boundary, not first native delivery callback.',
            'Angle and scalar gates are evaluated from sequential observations; exact callback input identity and order are not established.',
            'pending_action may be stale; selected action events are required as outcome evidence.',
            'World direction relative to first qualified case input detects the delivered opposite direction; caller may retain another reference.',
            'Terrain and camera geometry need separate capture review; this report does not certify them.'])
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([dict(case=c['case'],qualified=c['qualified'],pre=c['last_qualified_before_command'],
        opposite=c['first_qualified_opposite'],gate=c['first_open_angle_scalar_gate'],
        outcome79=c['outcome79'],outcome116_or117=c['outcome116_or117'],
        events=[(e['t'],e['action'],e['phase']) for e in c['qualified_events']]) for c in cases]))


if __name__=='__main__':
    main()
