"""Split sequential observations at clip switches; never join separate runs."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from project_paths import report_path


def clip_runs(record):
    if not record['actor_component_unchanged']:
        raise ValueError('Actor/component identity changed during capture')
    catalog=record.get('clip_catalog',{record['primary_resource_address']:record['primary_clip']})
    runs=[]
    for index,row in enumerate(record['rows']):
        resource=row.get('primary_resource_address',record['primary_resource_address'])
        if resource not in catalog:
            raise ValueError('Missing clip metadata')
        count=len(catalog[resource]['tracks'])
        if len(bytes.fromhex(row['primary_states_hex']))!=count*12:
            raise ValueError('Clip state size differs from metadata')
        if not runs or resource!=runs[-1][0]:
            runs.append((resource,[]))
        copied=deepcopy(row);copied['source_observation_index']=index
        runs[-1][1].append(copied)
    outputs=[]
    for resource,rows in runs:
        result=deepcopy(record)
        result.update(primary_resource_address=resource,primary_clip=deepcopy(catalog[resource]),
                      primary_track_count=len(catalog[resource]['tracks']),rows=rows)
        result['limitations']=record['limitations']+[
            'Contiguous clip run; root instance/link address metadata may describe initial capture only.']
        outputs.append(result)
    return outputs


def main():
    parser=argparse.ArgumentParser();parser.add_argument('record',type=Path)
    args=parser.parse_args()
    runs=clip_runs(json.loads(args.record.read_text()))
    paths=[]
    for index,run in enumerate(runs):
        path=report_path(f'{args.record.stem}-clip-run-{index:03}.json')
        path.write_text(json.dumps(run,indent=2));paths.append(str(path))
    print(json.dumps({'runs':len(runs),'reports':paths}))


if __name__=='__main__':main()
