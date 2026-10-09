"""Audit optional heading norm/time context; never infer callback-time flags."""
import argparse
import hashlib
import json
import math
import struct
from collections import Counter
from pathlib import Path
from jade_trace_consistency import rejection_reasons
from movement_suite import ROOT

def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def unpack(h,fmt='<f'):return struct.unpack(fmt,bytes.fromhex(h))[0]

def audit(path):
    run=json.loads(path.read_text())
    source=Path(next(c['parsed']['report'] for c in run['collectors']
        if 'capture_tracking_sequence.py' in ' '.join(c['command'])))
    if not source.is_absolute():source=ROOT/source
    raw=json.loads(source.read_text());rows=[]
    for s in raw['samples']:
        t=raw['start_performance_counter']+s['elapsed_seconds']-run['input_origin_performance_counter']
        if not 0<=t<=run['case']['duration']:continue
        norm=s.get('native_heading_norm_inputs',{});scale=s.get('native_heading_time_scale_inputs',{})
        norm_keys=('norm_present','pointer_unchanged','norm_unchanged','equals_selector_norm_pointer','pointer_identity_unchanged')
        norm_reasons=[key for key in norm_keys if norm.get(key) is not True]
        checks=scale.get('globals_unchanged',{})
        scale_keys=('0x1419a0290','0x1420c3430','0x1420c3450','0x14173cd70')
        scale_reasons=[key for key in scale_keys if checks.get(key) is not True]
        scale_reasons+=[key for key in ('source_ushort_present','source_ushort_unchanged') if scale.get(key) is not True]
        row=dict(index=s['index'],t=t,action=s['current_action_index_a8'],pose_reasons=rejection_reasons(s),
            norm_reasons=norm_reasons,time_scale_reasons=scale_reasons,
            raw_norm=norm,raw_time_scale=scale,flag=scale.get('flag_1419a0290'),
            flag_qualified=checks.get('0x1419a0290') is True)
        if not norm_reasons:row['qualified_global_norm']=unpack(norm['norm_hex'])
        if not scale_reasons:
            globals_=scale['globals_hex'];substep=unpack(globals_['0x1420c3430'])
            divisor=unpack(globals_['0x14173cd70']);duration=unpack(scale['source_ushort_hex'],'<H')
            row.update(substep3430=substep,source_u16=duration,constant_cd70=divisor)
            if divisor!=0. and duration!=0:
                denominator=f32(float(duration)/divisor);factor=f32(substep/denominator)
                row.update(hypothetical_flag1_denominator=denominator,hypothetical_flag1_factor=factor,
                    finite_factor=math.isfinite(factor))
            else:
                row['factor_invalid_reason']='Zero divisor/source duration; native division semantics not evaluated by this audit'
        rows.append(row)
    flagrows=[r for r in rows if r['flag_qualified']]
    norms=[r for r in rows if not r['norm_reasons']]
    factors=[r for r in rows if not r['time_scale_reasons']]
    return dict(run=str(path),source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),rows=rows,
        summary=dict(rows=len(rows),qualified_norm_pointer=len(norms),
            norm_pointer_values=sorted(set(r['raw_norm']['norm_address'] for r in norms)),
            all_observed_flag_histogram=dict(Counter(str(r['flag']) for r in rows)),
            qualified_flag_histogram=dict(Counter(str(r['flag']) for r in flagrows)),
            qualified_time_scale_inputs=len(factors),
            pose_and_context_qualified=sum(not r['pose_reasons'] and not r['norm_reasons'] and not r['time_scale_reasons'] for r in rows),
            source_u16_values=sorted(set(r['source_u16'] for r in factors)),
            substep3430_range=[min((r['substep3430'] for r in factors),default=None),max((r['substep3430'] for r in factors),default=None)],
            hypothetical_flag1_factors=sorted(set(r.get('hypothetical_flag1_factor') for r in factors if 'hypothetical_flag1_factor' in r))))

def main():
    p=argparse.ArgumentParser();p.add_argument('runs',type=Path,nargs='+');p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=dict(schema='native-heading-context-audit-v1',runs=[audit(path) for path in a.runs],limits=[
        'Qualification applies to sequential snapshots, not atomic callback inputs.',
        '1419A0290 is transient animation-manager context. Stable flag0 does not prove flag0 at heading callback.',
        'Recorded pointer equality proves shared scalar for qualified observations only.',
        'Hypothetical flag1 factor is derived from observed context; no actual application during callback is claimed.',
        'Source duration/substep globals may belong to the last animation entry, not the current Jade callback.'])
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps([r['summary'] for r in result['runs']],indent=2))

if __name__=='__main__':main()
