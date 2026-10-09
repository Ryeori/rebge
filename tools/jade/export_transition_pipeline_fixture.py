"""Native transition local outputs and source inputs, selected by existing guards."""
import json,hashlib
from pathlib import Path
from project_paths import ASSET_ROOT,report_path
from jade_target_hierarchy import snapshot_target_nodes

def main():
    provenance=json.loads(report_path('stage43-bevy-local-blend-provenance.json').read_text())
    source=Path(provenance['source']);samples={s['index']:s for s in json.loads(source.read_text())['samples']}
    rig=json.loads((ASSET_ROOT/'skeletons/sally/gao-parent-links.json').read_text())
    grouped={}
    for row in provenance['rows']:
        if row['slot']==0:continue
        grouped.setdefault(row['sample'],dict(keys=row['source_keys'],slots=[]))['slots'].append(row['slot'])
    cases=[]
    for index,row in grouped.items():
        sample=samples[index];objects={o['slot']:o for o in sample['objects']}
        nodes=[dict(address=a,flags=n['flags'],world=n['world_matrix'],world_flags=n['world_flags'],parent=n.get('parent_address'),local=n.get('local_matrix'),local_flags=n.get('local_flags')) for a,n in snapshot_target_nodes(sample).items()]
        states=lambda name:[dict(track=t['track_index'],index=t['frame_index'],elapsed=t['elapsed_seconds']) for t in sample[name+'_clip']['tracks'] if t['indexed_slot'] not in (0,65535)]
        cases.append(dict(sample=index,keys=row['keys'],nodes=nodes,bone_addresses=[int(objects[b['slot']]['address'],16) if b['slot'] is not None else int(sample['actor']['address'],16) for b in rig['objects']],
            outgoing=states('transition'),primary=states('primary'),ratio=sample['transition_clip']['tracks'][0]['auxiliary_f32'],expected=[dict(bone=next(i for i,b in enumerate(rig['objects']) if b['slot']==slot),local=objects[slot]['linked_local_matrix']) for slot in row['slots']]))
    output=report_path('stage43-transition-pipeline-native.json');output.write_text(json.dumps(dict(source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),cases=cases,
        selection='Existing qualified native blend provenance rows; root slot0 excluded before evaluation; no predicted-error filtering.',limitations=['Current restored native locals provide unwritten-channel inputs. Selected comparisons have both position and rotation source channels. Root and tracking writers excluded.'])))
    print(json.dumps(dict(report=str(output),samples=len(cases),locals=sum(len(c['expected']) for c in cases))))
if __name__=='__main__':main()
