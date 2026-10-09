"""Qualify sight_banking inputs without claiming atomic native callback order."""
import argparse
import hashlib
import json
import math
import struct
from collections import Counter
from pathlib import Path
from jade_trace_consistency import rejection_reasons, pair_candidate
from movement_suite import ROOT

def f32(v):
    return struct.unpack('<f',struct.pack('<f',v))[0]

def scalar(h,fmt='<f'):
    return struct.unpack(fmt,bytes.fromhex(h))[0]

def normalized(v):
    squared=f32(f32(f32(v[1]*v[1])+f32(v[0]*v[0]))+f32(v[2]*v[2]))
    inverse=f32(1./f32(math.sqrt(squared)))
    return [f32(x*inverse) for x in v]

def audit(path):
    run=json.loads(path.read_text())
    source=Path(next(c['parsed']['report'] for c in run['collectors']
        if 'capture_tracking_sequence.py' in ' '.join(c['command'])))
    if not source.is_absolute():source=ROOT/source
    raw=json.loads(source.read_text());rows=[];samples={}
    for s in raw['samples']:
        t=raw['start_performance_counter']+s['elapsed_seconds']-run['input_origin_performance_counter']
        if not 0<=t<=run['case']['duration']:continue
        h=s.get('native_heading_inputs',{});checks={key:h.get(key) for key in
            ('pointer_identity_unchanged','brain_fields_unchanged','dt_unchanged',
             'runtime_velocity_present','runtime_velocity_unchanged',
             'descriptor_byte_23_present','descriptor_byte_23_unchanged')}
        reasons=[key for key,value in checks.items() if value is not True]
        reasons+=['filter_inputs'] if s.get('native_direction_filter_inputs',{}).get('unchanged') is not True else []
        reasons+=['selector_inputs'] if s.get('selector_inputs',{}).get('unchanged') is not True else []
        row=dict(index=s['index'],t=t,action=s['current_action_index_a8'],
            update_pass=s['update_pass_before'],checks=checks,input_reasons=reasons,
            pose_reasons=rejection_reasons(s),raw_heading_inputs=h)
        if not reasons:
            fields=h['brain_fields_hex'];v=bytes.fromhex(h['runtime_velocity_10_2b_hex'])
            vx,vy=struct.unpack_from('<2f',v);scale=struct.unpack_from('<f',v,0x18)[0]
            vx=f32(vx*scale);vy=f32(vy*scale)
            speed=f32(math.sqrt(f32(f32(f32(vy*vy)+f32(vx*vx))+0.)))
            response=scalar(fields['0x10d0']);dt=scalar(h['dt_1420a3318_hex'])
            factor=f32(f32(f32(min(max(speed,3.),4.5)*response)*f32(.03))*f32(dt*30.))
            descriptor=bytes.fromhex(h['descriptor_byte_23_hex'])[0]
            gate=scalar(fields['0x1dc'],'<i');mode=scalar(fields['0x10e4'],'<i')
            selector48=s['selector_inputs']['selection_value_48']
            row.update(response_10d0=response,mode_10e4=mode,gate_1dc=gate,
                response_1198=scalar(fields['0x1198']),dt=dt,
                velocity_components_before_scalar=list(struct.unpack_from('<2f',v)),
                velocity_scalar_28=scale,horizontal_velocity_norm=speed,
                ordinary_factor_unclamped=factor,ordinary_factor=min(max(factor,0.),1.),
                descriptor_byte_23=descriptor,descriptor_gate_open=descriptor<128,
                selector48=selector48,caller48_gate_open=selector48>f32(.35),
                ordinary_branch_candidate=gate!=0 and descriptor<128 and mode!=1 and selector48>f32(.35),
                filtered_direction=list(struct.unpack('<3f',bytes.fromhex(s['native_direction_filter_inputs']['filtered_direction_1e4_hex']))),
                actor_forward=[-s['actor']['world_matrix'][i] for i in (4,5,6)])
            turn=s.get('standing_turn_inputs',{})
            row['global_norm_qualified']=turn.get('unchanged') is True
            row['ordinary_actor_forward']=not (int(s['actor']['flags'],16)&0x400000)
            if (row['global_norm_qualified'] and row['ordinary_actor_forward']
                    and row['caller48_gate_open'] and any(row['filtered_direction'])):
                norm=struct.unpack_from('<f',bytes.fromhex(turn['direction_38_norm_74_hex']),0x3c)[0]
                a=normalized(row['actor_forward']);b=normalized(row['filtered_direction'])
                cosine=f32(f32(f32(a[1]*b[1])+f32(a[0]*b[0]))+f32(a[2]*b[2]))
                angle=(0. if cosine>=1. else f32(math.pi) if cosine<=-1. else f32(math.acos(cosine)))
                cross_z=f32(f32(a[0]*b[1])-f32(a[1]*b[0]))
                if cross_z<0.:angle=-angle
                cap=f32(norm/f32(3.5));sign=-1. if angle<0. else 1.
                timepart=f32(f32(dt*30.)*row['response_1198'])
                yaw=f32(f32(f32(sign*min(abs(angle),cap))*f32(.9))*timepart)
                planar=f32(math.atan2(a[0]*b[1]-a[1]*b[0],a[0]*b[0]+a[1]*b[1]))
                row.update(global_norm=norm,normalized_direction_cosine=cosine,
                    derived_signed_angle=angle,direct_yaw_norm_cap=cap,
                    diagnostic_planar_atan2_angle=planar,
                    diagnostic_planar_angle_difference=abs(planar-angle),
                    derived_direct_yaw_parameter=yaw,
                    direct_yaw_parameter_candidate=mode==1 and gate!=0 and descriptor<128
                        and selector48>f32(.35))
        rows.append(row);samples[s['index']]=s
    pairs=[]
    for a,b in zip(rows,rows[1:]):
        candidate=pair_candidate(samples[a['index']],samples[b['index']])
        reasons=candidate['reasons']+a['input_reasons']+b['input_reasons']
        if not reasons and a['raw_heading_inputs']['brain_address']!=b['raw_heading_inputs']['brain_address']:
            reasons.append('brain_identity_changed')
        if not reasons and (not a['caller48_gate_open'] or not b['caller48_gate_open']):
            reasons.append('caller_gate_not_open_both')
        p=dict(first=a['index'],second=b['index'],candidate=not reasons,reasons=sorted(set(reasons)),
            native_callback_count_proven=False)
        if not reasons:
            alpha=min(max(f32(b['dt']*5.),0.),1.)
            expected=f32(f32(f32(1.-alpha)*a['response_10d0'])+f32(alpha*3.))
            p.update(observed_previous=a['response_10d0'],observed_next=b['response_10d0'],
                expected_one_callback=expected,exact_f32_match=expected==b['response_10d0'],
                informative=a['response_10d0']!=3. or b['response_10d0']!=3.)
        pairs.append(p)
    qualified=[r for r in rows if not r['input_reasons']]
    timeline=[]
    for r in qualified:
        if not timeline or (timeline[-1]['action'],timeline[-1]['mode'])!=(r['action'],r['mode_10e4']):
            timeline.append(dict(first_index=r['index'],t_start=r['t'],action=r['action'],mode=r['mode_10e4'],
                first_speed=r['horizontal_velocity_norm'],first_1198=r['response_1198']))
        timeline[-1].update(last_index=r['index'],t_end=r['t'],last_speed=r['horizontal_velocity_norm'],last_1198=r['response_1198'])
    return dict(run=str(path),source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        case=run['case']['id'],rows=rows,pairs=pairs,timeline=timeline,
        summary=dict(rows=len(rows),input_qualified=len(qualified),
            pose_and_inputs_qualified=sum(not r['pose_reasons'] for r in qualified),
            modes=dict(Counter(str(r['mode_10e4']) for r in qualified)),
            responses_10d0=sorted(set(r['response_10d0'] for r in qualified)),
            velocity_scalars=sorted(set(r['velocity_scalar_28'] for r in qualified)),
            descriptor_bytes=sorted(set(r['descriptor_byte_23'] for r in qualified)),
            ordinary_branch_candidates=sum(r['ordinary_branch_candidate'] for r in qualified),
            direct_yaw_branch_candidates=sum(r.get('direct_yaw_parameter_candidate',False) for r in qualified),
            max_diagnostic_planar_angle_difference=max((r.get('diagnostic_planar_angle_difference',0.)
                                                       for r in qualified),default=0.),
            adjacent_candidates=sum(p['candidate'] for p in pairs),
            informative_recurrences=sum(p.get('informative',False) for p in pairs)))

def main():
    p=argparse.ArgumentParser();p.add_argument('runs',type=Path,nargs='+');p.add_argument('--output',type=Path,required=True)
    provenance=[]
    for name in ('agent-jade-sight-banking-20261009.json',
                 'agent-jade-heading-constants-main-20261009.json',
                 'agent-jade-heading-constant-scale-20261009.json',
                 'agent-jade-heading-norm-gate-20261009.json',
                 'agent-jade-heading-yaw-constant-20261010.json',
                 'agent-jade-heading-direct-yaw-branch-listing-20261010.json',
                 'agent-jade-heading-direct-yaw-writer-listing-20261010.json'):
        path=ROOT/'reports'/'ghidra'/'raw'/name
        provenance.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    a=p.parse_args();result=dict(schema='native-heading-input-audit-v1',algorithm_sources=provenance,
        runs=[audit(path) for path in a.runs],
        limits=['Stable sequential reads are not atomic callback inputs.',
            'Update-pass adjacency does not prove one sight_banking invocation or its prior inputs.',
            'Factor is evaluated from independently recorded inputs and Ghidra constants; its computed output is not a recorded heading oracle.',
            'Response equal to equilibrium3 cannot verify recurrence or callback count.',
            'Derived signed angle/yaw are diagnostic numerical evaluations, not native recorded outputs; 140b33710 optional time scaling globals were not captured.',
            'Special actor orientation, direct yaw mode1 and banking/up effects require separate validation.'])
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([r['summary'] for r in result['runs']],indent=2))

if __name__=='__main__':main()
