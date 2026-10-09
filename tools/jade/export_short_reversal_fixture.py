"""Export measured short-reversal branch inputs and external delivery timeline."""
import argparse
import hashlib
import json
from pathlib import Path
from movement_suite import ROOT


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('audit',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    source=json.loads(args.audit.read_text())
    cases=[]
    for observed in source['cases']:
        run_path=Path(observed['run'])
        if not run_path.is_absolute():run_path=ROOT/run_path
        if digest(run_path)!=observed['run_sha256']:
            raise ValueError('Run source changed')
        run=json.loads(run_path.read_text())
        raw_path=Path(observed['source'])
        if digest(raw_path)!=observed['source_sha256']:
            raise ValueError('Raw source changed')
        branch=next(e for e in observed['qualified_events']
                    if e['t']>=observed['command_opposite_t'] and e['action'] in (79,116,117))
        cases.append(dict(case=observed['case'],duration=run['case']['duration'],
            run=str(run_path.relative_to(ROOT)),run_sha256=digest(run_path),
            source=str(raw_path.relative_to(ROOT)),source_sha256=digest(raw_path),
            catalog_sha256_at_capture=run['catalog_sha256'],catalog_points=run['case']['points'],
            command_opposite_t=observed['command_opposite_t'],
            input_origin_performance_counter=run['input_origin_performance_counter'],
            timeline=[dict(t=e['performance_counter']-run['input_origin_performance_counter'],
                           elapsed=e['elapsed'],x=e['x'],y=e['y'],r2=e['r2']) for e in run['events']],
            initial_case_input=observed['initial_case_input'],
            last_qualified_before_command=observed['last_qualified_before_command'],
            first_qualified_opposite=observed['first_qualified_opposite'],
            first_open_angle_scalar_gate=observed['first_open_angle_scalar_gate'],
            qualified_gate_rows=observed['gate_candidate_rows'],
            first_observed_branch=branch,
            expected_branch_family='moving79' if observed['outcome79'] else 'standing116_117',
            observed_branch_action=branch['action'],
            expected_action_phase_sequence=[dict(t=e['t'],action=e['action'],phase=e['phase'])
                                            for e in observed['qualified_events']],
            qualification=dict(accepted=observed['qualified'],rejected=observed['rejected'])))
    result=dict(schema='native-short-reversal-fixture-v1',audit=str(args.audit),audit_sha256=digest(args.audit),
        cases=cases,limits=[
            'Expected branch families come from independent recorded action selection, not the reconstruction.',
            'Qualified gate rows are stable sequential observations, not atomic callback inputs. First gate observation may occur after actual selection.',
            'Case0.45 first qualified opposite is already action79; use measured last_action3/speed as bounded context rather than asserting a preselection callback capture.',
            'External timeline floats are before DS4 quantization/device normalization and native Global input filtering. Do not assert exact delivery or simulation dt.',
            'Source world direction and actor forward come from measured inputs; convert sourceXYZ consistently. Do not feed observed actor forward back into integrated simulator each frame.',
            'Observe branch family when simulator mirror geometry differs; recorded116 versus117 exact side requires identical geometry.',
            'A later speed crossing2.5 must not retroactively change an already accepted queued branch. Pending action alone is not fresh queue proof.',
            'Action-phase sequence is evidence, not a claim of whole-pose parity.'])
    args.output.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(output=str(args.output),cases=[dict(case=c['case'],family=c['expected_branch_family'],
                    action=c['observed_branch_action']) for c in cases])))


if __name__=='__main__':
    main()
