"""Terminal root publication -> reference entry copy; fixed observed repeat edges."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from jade_animation_transition import f32
from jade_trace_consistency import pair_candidate
from jade_target_hierarchy import raw_affine_product
from jade_pose import rotation_matrix
from jade_rotation_channel import rotation_at_state
from jade_translation_channel import translation_at_state
from jade_basis_normalize import normalize_basis
from match_sally_runtime_clip import signature
from project_paths import ASSET_ROOT, report_path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('sequence',type=Path);args=parser.parse_args()
    raw=args.sequence.read_bytes();samples=json.loads(raw)['samples'];sources={}
    for path in sorted((ASSET_ROOT/'animations/sally/local-samples').glob('*.json')):
        source=json.loads(path.read_text())
        sources.setdefault(json.dumps(signature(source['tracks'])),[]).append((path.stem,source))
    cases=[];skipped=[]
    for a,b in zip(samples,samples[1:]):
        pa,pb=(bytes.fromhex(s['component_aa_b5_hex']) for s in (a,b))
        if pb[3]!=((pa[3]+1)&255) or pa[:3]!=pb[:3]:continue
        reasons=pair_candidate(a,b)['reasons']
        if a['primary_clip']['resource_address']!=b['primary_clip']['resource_address']:
            reasons.append('resource_changed')
        if any(not s.get('actor_reference_unchanged') for s in (a,b)):
            reasons.append('reference_changed')
        if any(int(s['actor']['flags'],16)&0x400000 for s in (a,b)):
            reasons.append('linked_actor_input_missing')
        if reasons:
            skipped.append(dict(before=a['index'],after=b['index'],reasons=reasons));continue
        try:
            choices=sources.get(json.dumps(signature(a['primary_clip']['tracks'],True)),[])
            if len(choices)!=1:raise ValueError('Unique source required')
            key,source=choices[0]
            if any(t['short1']!=65535 for t in source['tracks'][:2]):
                raise ValueError('First root pair required')
            q=rotation_at_state(source['tracks'][0],dict(frame_index=len(source['tracks'][0]['frames'])-1,elapsed_seconds=0.))
            p=translation_at_state(source['tracks'][1],dict(frame_index=len(source['tracks'][1]['frames'])-1,elapsed_seconds=0.))
            if q is None or p is None:raise ValueError('Terminal root channels missing')
            old=struct.unpack('<16fI',bytes.fromhex(a['actor_reference_matrix_hex']))
            observed=struct.unpack('<16fI',bytes.fromhex(b['actor_reference_matrix_hex']))
            if old[16]&0x38:raise ValueError('Scaled/alternate reference unsupported')
            terminal=rotation_matrix(q)
            terminal=raw_affine_product(terminal,old[:16],4,old[16])[0] if old[16]&0x3c else terminal
            for row in range(3):
                order=(0,1,2) if row==0 else (1,0,2)
                terms=[f32(p[k]*old[k*4+row]) for k in order]
                terminal[12+row]=f32(f32(f32(terms[0]+terms[1])+terms[2])+old[12+row])
            # Root consumers replace only basis/position; preserve all other actor bytes.
            predicted=list(a['actor']['world_matrix'][:16])
            for i in (0,1,2,4,5,6,8,9,10,12,13,14):predicted[i]=terminal[i]
            flags=int(a['actor']['world_matrix'][16])|6
            gate=(a.get('reference_entry_gate_u32') if 'reference_entry_gate_u32' in a else
                  int(a['reference_entry_manager_address'],16)&0xffffffff)
            basis_indices=(0,1,2,4,5,6,8,9,10)
            normalized=normalize_basis(predicted)
            cases.append(dict(before=a['index'],after=b['index'],source=key,gate_u32=gate,
                prior_reference=list(old[:16]),prior_reference_flags=old[16],
                terminal_rotation=q,terminal_position=p,prior_actor=a['actor']['world_matrix'][:16],
                prior_actor_flags=int(a['actor']['world_matrix'][16]),
                predicted_reference=predicted,predicted_flags=flags,
                observed_reference=list(observed[:16]),observed_flags=observed[16],
                maximum_error=max(abs(x-y) for x,y in zip(predicted,observed[:16])),flags_match=flags==observed[16],
                basis_error=max(abs(predicted[i]-observed[i]) for i in basis_indices),
                position_error=max(abs(predicted[i]-observed[i]) for i in (12,13,14)),
                normalization_hypothesis_basis_error=max(abs(normalized[i]-observed[i]) for i in basis_indices)))
        except (ValueError,NotImplementedError) as error:
            skipped.append(dict(before=a['index'],after=b['index'],reasons=[str(error)]))
    result=dict(source_record=str(args.sequence),source_sha256=hashlib.sha256(raw).hexdigest(),cases=cases,skipped=skipped,
        limitations=['Fixed qualified repeat edges only; sequential prior matrices are not atomic callback inputs.',
                    'Direct actor/root transform pair only; no collision, linked actor or phase change reconstruction.',
                    '030317 gate was captured as8bytes; low32 recovered after CMP dword verification, raw record unchanged.'])
    path=report_path(args.sequence.stem+'-reference-entry.json');path.write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(report=str(path),cases=len(cases),skipped=skipped,
        errors=[dict(before=c['before'],after=c['after'],error=c['maximum_error'],flags_match=c['flags_match']) for c in cases])))


if __name__=='__main__':main()
