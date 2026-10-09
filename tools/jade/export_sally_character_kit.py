"""Private, traceable Sally resource kit and editable OBJ of captured pose."""
import json,hashlib
from pathlib import Path
from project_paths import ASSET_ROOT,report_path

def main():
 variants=json.loads(report_path('stage4-sally-variant-geometry.json').read_text());deps=json.loads(report_path('stage4-sally-variant-dependencies.json').read_text());verification=json.loads(report_path('stage4-sally-runtime-verification.json').read_text())
 scene_path=ASSET_ROOT/'scenes/sally-runtime-skin/scene.json';scene=json.loads(scene_path.read_text());out=ASSET_ROOT/'models/characters/sally';out.mkdir(parents=True,exist_ok=True)
 rows=[]
 def asset(path,kind,key=None,source_sha=None):
  path=Path(path);path=path if path.is_absolute() else ASSET_ROOT/path
  if not path.is_file():raise ValueError('Missing kit resource: '+str(path))
  row={'type':kind,'path':path.relative_to(ASSET_ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
  if key:row['source_key']=key
  if source_sha:row['source_sha256']=source_sha
  rows.append(row)
 for g in variants['geometry']:asset(g['export_path'],'mesh',g['key'],g['source_sha256'])
 for key,m in deps['materials'].items():asset(m['path'],'material',key,m.get('source_sha256'))
 for key,t in deps['textures'].items():asset(t['path'],'texture',key,t.get('source_sha256'))
 for p in sorted((ASSET_ROOT/'animations/sally/local-samples').glob('*.json')):asset(p,'animation-channels',p.stem)
 for p in sorted((ASSET_ROOT/'skeletons/sally').glob('*.json')):asset(p,'skeleton-binding')
 obj=['# Captured native palette applied to offline source meshes. Static pose, not animated rig.','mtllib native-pose.mtl'];mtl=[];vertex=1
 for batch_index,b in enumerate(scene['batches']):
  name='part_'+b['object']+'_batch_'+str(batch_index);obj.extend(['o '+name,'usemtl '+name]);mtl.extend(['newmtl '+name,'Kd 1 1 1','d 1'])
  if b['texture']:mtl.append('map_Kd '+Path('../../../'+b['texture']).as_posix())
  v=b['vertices'];n=len(v)//5
  if len(v)%15:raise ValueError('Incomplete triangle batch')
  for i in range(n):
   x,y,z,u,w=v[i*5:i*5+5];obj.append(f'v {x:.9g} {z:.9g} {-y:.9g}');obj.append(f'vt {u:.9g} {1-w:.9g}')
  for i in range(0,n,3):obj.append('f '+' '.join(f'{vertex+j}/{vertex+j}' for j in (i,i+1,i+2)))
  vertex+=n
 (out/'native-pose.obj').write_text('\n'.join(obj)+'\n');(out/'native-pose.mtl').write_text('\n'.join(mtl)+'\n');asset(out/'native-pose.obj','static-pose-obj');asset(out/'native-pose.mtl','obj-materials');asset(scene_path,'bevy-static-pose')
 manifest={'schema':'jade-sally-character-kit-v1','actor_key':'71003F5A','indexed_source_list':'7100AF2A','joint_slots':47,'variants':variants['links'],'resources':rows,'runtime_evidence':verification['snapshot'],'palette_max_abs_error':verification['max_palette_error'],'geometry_evidence':verification['geometry'],'limits':['Private extraction from user-owned installation.','OBJ/Bevy scene is a static captured pose, not autonomous animation playback.','Original GPU screenshot was black; pixel/frame parity not established.','Native vertex duplication/reorder identified by exact coordinate-set equality; topology/output buffers not yet compared.','Source materials preserve opaque data; simplified preview uses first colour stream.','Animation control VM, transitions, physics, camera and full game remain incomplete.']}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2));report_path('stage4-sally-character-kit.json').write_text(json.dumps({'manifest':str(out/'manifest.json'),'resources':len(rows),'animation_resources':sum(r['type']=='animation-channels' for r in rows),'triangles':(vertex-1)//3,'limits':manifest['limits']},indent=2));print(json.dumps({'manifest':str(out/'manifest.json'),'resources':len(rows),'triangles':(vertex-1)//3}))
if __name__=='__main__':main()
