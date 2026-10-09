"""Locate source-local pose writes in the readonly publication observation.

Matching a source-local pose identifies an observed state, not callback entry.
"""
import argparse
import json
import struct
from copy import deepcopy
from pathlib import Path
from jade_modifier24 import _quaternion_matrix
from match_sally_runtime_clip import signature
from probe_transition_pose import channels
from project_paths import ASSET_ROOT,report_path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('snapshot',type=Path)
    args=parser.parse_args();record=json.loads(args.snapshot.read_text())
    samples=json.loads(Path(record['source_snapshot']).read_text())['samples']
    matching=[s for s in samples if s['primary_clip']['resource_address']==record['primary_resource_address']]
    if not matching and 'primary_clip' not in record:raise ValueError('Observed clip resource absent from full sequence')
    template=(record['primary_clip']['tracks'] if 'primary_clip' in record else matching[-1]['primary_clip']['tracks'])
    candidates=[]
    for path in (ASSET_ROOT/'animations/sally/local-samples').glob('*.json'):
        source=json.loads(path.read_text())
        if signature(source['tracks'])==signature(template,True):candidates.append((path.stem,source))
    if len(candidates)!=1:raise ValueError('Unique source clip required')
    key,source=candidates[0];rows=[];skipped=[]
    for index,row in enumerate(record['rows']):
        if not row['primary_clip_unchanged']:continue
        states=deepcopy(template);raw=bytes.fromhex(row['primary_states_hex'])
        for i,state in enumerate(states):
            elapsed,aux,frame,flags=struct.unpack_from('<ffHH',raw,i*12)
            state.update(elapsed_seconds=elapsed,auxiliary_f32=aux,frame_index=frame,state_flags=flags)
        values,missing=channels(source,states)
        if missing:
            skipped.append(dict(index=index,missing=missing));continue
        for slot in (9,10,20):
            value=values.get(slot,{})
            if 'quaternion_xyzw' not in value:continue
            expected=_quaternion_matrix(value['quaternion_xyzw'])
            actual=struct.unpack('<16fI',bytes.fromhex(row['matrices'][f'{slot}_local']))
            rows.append(dict(index=index,slot=slot,elapsed_seconds=row['elapsed_seconds'],
                rotation_error=max(abs(expected[i]-actual[i]) for i in (0,1,2,4,5,6,8,9,10)),
                pass_before=row['pass_before'],pass_after=row['pass_after']))
    summary=dict(source_key=key,checked=len(rows),source_local_matches=sum(x['rotation_error']<=1e-5 for x in rows),
        by_slot={slot:dict(checked=sum(x['slot']==slot for x in rows),
                          matched=sum(x['slot']==slot and x['rotation_error']<=1e-5 for x in rows)) for slot in (9,10,20)})
    result=dict(summary=summary,rows=rows,skipped=skipped,
        limitations=['Sequential reads; no callback-entry provenance.',
                    'Primary-only source comparison; transition blend not reconstructed here.'])
    report_path(args.snapshot.stem+'-source-pose.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(summary))


if __name__=='__main__':main()
