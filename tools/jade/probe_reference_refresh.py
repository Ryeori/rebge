"""Conditional identity-root refresh diagnostic using saved temporal readings."""
import argparse
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path
from jade_trace_consistency import rejection_reasons
from match_sally_runtime_clip import signature
from probe_motion_pose import root_translation
from jade_actor_reference import refresh_reference
from jade_target_hierarchy import IDENTITY
from jade_pose import rotation_matrix
from jade_rotation_channel import rotation_at_state
from jade_translation_channel import translation_at_state
from project_paths import ASSET_ROOT,report_path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('snapshot',type=Path)
    args=parser.parse_args();raw=args.snapshot.read_bytes();sequence=json.loads(raw)
    sources={}
    for path in sorted((ASSET_ROOT/'animations/sally/local-samples').glob('*.json')):
        source=json.loads(path.read_text())
        sources.setdefault(json.dumps(signature(source['tracks'])),[]).append((path.stem,source))
    rows=[];skipped=[]
    for sample in sequence['samples']:
        reasons=rejection_reasons(sample)
        if reasons:
            skipped.append(dict(sample=sample['index'],reasons=reasons));continue
        try:
            if not sample.get('actor_reference_unchanged'):raise ValueError('Reference changed or absent')
            if int(sample['actor']['flags'],16)&0x400000:raise ValueError('Linked actor input unavailable')
            tracks=sample['primary_clip']['tracks']
            candidates=sources.get(json.dumps(signature(tracks,True)),[])
            if len(candidates)!=1:raise ValueError('Primary source not unique')
            key,source=candidates[0]
            root=IDENTITY.copy();root[12:15]=root_translation(source,tracks)
            actor=sample['actor']['world_matrix']
            expected,_=refresh_reference(root,2,actor[:16],int(actor[16]))
            actual=struct.unpack('<16fI',bytes.fromhex(sample['actor_reference_matrix_hex']))
            row=dict(sample=sample['index'],key=key,active_slots=sample['component_flags_u16']>>8&15,
                basis_error=max(abs(expected[i]-actual[i]) for i in (0,1,2,4,5,6,8,9,10)),
                position_error=max(abs(expected[i]-actual[i]) for i in (12,13,14)))
            # Separate hypothesis: local root channels at captured clocks, evaluated
            # against identity. This is not a captured zero-delta callback input.
            if row['active_slots']==1 and all(t['short1']==65535 for t in source['tracks'][:2]):
                q=rotation_at_state(source['tracks'][0],tracks[0])
                p=translation_at_state(source['tracks'][1],tracks[1])
                if q is not None and p is not None:
                    root=rotation_matrix(q);root[12:15]=p
                    candidate,flags=refresh_reference(root,6,actor[:16],int(actor[16]))
                    row['local_root_hypothesis']=dict(root=root,root_flags=6,
                        saved_actor=actor[:16],saved_actor_flags=int(actor[16]),
                        predicted_reference=candidate,predicted_flags=flags,observed_reference=list(actual),
                        basis_error=max(abs(candidate[i]-actual[i]) for i in (0,1,2,4,5,6,8,9,10)),
                        position_error=max(abs(candidate[i]-actual[i]) for i in (12,13,14)))
            rows.append(row)
        except (ValueError,NotImplementedError) as error:
            skipped.append(dict(sample=sample['index'],reason=str(error)))
    result=dict(snapshot=str(args.snapshot),source_sha256=hashlib.sha256(raw).hexdigest(),rows=rows,skipped=skipped,
        limitation='Conditional identity root and current actor world; refresh-time saved actor input not proven.')
    for field in ('basis','position'):
        errors=[r[field+'_error'] for r in rows]
        result[field]=dict(checked=len(errors),matched=sum(e<=1e-5 for e in errors),maximum_error=max(errors,default=None))
    result['source_counts']=dict(Counter(r['key'] for r in rows))
    candidates=[r['local_root_hypothesis'] for r in rows if 'local_root_hypothesis' in r]
    result['local_root_hypothesis']={field:dict(checked=len(candidates),
        matched=sum(r[field+'_error']<=1e-5 for r in candidates),
        maximum_error=max((r[field+'_error'] for r in candidates),default=None))
        for field in ('basis','position')}
    report_path(args.snapshot.stem+'-reference-refresh.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','skipped')}))
    print('skipped',len(skipped))


if __name__=='__main__':main()
