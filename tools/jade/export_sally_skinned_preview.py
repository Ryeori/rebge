"""Explicit diagnostic skin snapshot, not a native captured frame."""
import json,math,argparse
from pathlib import Path
from jade_pose import affine_product
from jade_skin import deform_vertices,compose_skin_matrix
from project_paths import ASSET_ROOT,report_path

def main():
 parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group();group.add_argument('--source-initial-skin-matrices',action='store_true');group.add_argument('--source-gao-world',action='store_true');group.add_argument('--runtime-snapshot',type=Path);args=parser.parse_args()
 captured=json.loads(args.runtime_snapshot.read_text()) if args.runtime_snapshot else None
 if captured and captured['status']!='captured':raise ValueError('Runtime actor was not captured')
 initial=json.loads(report_path('stage4-sally-source-skin-matrices.json').read_text())['matrices'] if args.source_initial_skin_matrices else None
 dependencies=json.loads(report_path('stage4-sally-variant-dependencies.json').read_text());variants=json.loads(report_path('stage4-sally-variant-geometry.json').read_text());parts=json.loads(report_path('stage4-sally-all-parts.json').read_text())['objects'];pose=next(p for p in json.loads(report_path('stage4-sally-attached-world-snapshots.json').read_text())['snapshots'] if p['resource_key']=='7100B0E7');assert pose['complete_local_snapshot']
 keys=[p['key'] for p in parts];objects={p['key']:p for p in variants['objects']};skins={s['gao']:s for s in dependencies['skins']};batches=[];allpoints=[];selected=[]
 if args.source_gao_world:pose['jade_world_matrices']={p['key']:p['gao']['matrix'] for p in parts}
 def materials(key):
  row=dependencies['materials'][key]
  if row['kind']==4:return [v for child in row['materials'] for v in materials(child)]
  return [row['layers'][0]['texture'] if row.get('layers') else None]
 for link in variants['links']:
  if link['variant']!=(captured['selected_variants'][link['slot']] if captured else 1):continue
  o=objects[link['gao']];g=o['gao'];refs=g.get('visual_keys',[])
  if len(refs)!=2:continue
  mesh=json.loads((ASSET_ROOT/'models/meshes'/('sally-'+refs[0]+'.json')).read_text());skin=skins.get(o['key']);ext=mesh['extended_header'];positions=mesh['positions'];runtime={}
  if ext and skin:
   # Selected clone visual retains source flags from visual block. Read by gao_prefix next export.
   mirror=not bool(g.get('visual_flags',0)&0x8000)
   for record in ext['records']:
    binding=skin['bindings'][record['index_u16']];slot=binding['matrix_index'];assert slot<len(keys)
    bind=record['matrix'][:]
    bone=captured['palette']['matrices'][slot] if captured else None
    runtime[record['index_u16']]=compose_skin_matrix(bind,record['matrix_flags'],bone['matrix'] if bone else initial[slot]['matrix'] if initial else pose['jade_world_matrices'][keys[slot]],bone['flags'] if bone else initial[slot]['flags'] if initial else 6,mirror)
   positions=deform_vertices(positions,ext['records'],runtime)
  else:
   m=captured['palette']['matrices'][link['slot']]['matrix'] if captured else pose['jade_world_matrices'][keys[link['slot']]];positions=[[sum(p[j]*m[j*4+i] for j in range(3))+m[12+i] for i in range(3)] for p in positions]
  selected.append(link);textures=materials(refs[1])
  for sub in mesh['submeshes']:
   vertices=[];selector=sub['unknown'];tex=textures[selector] if selector<len(textures) else textures[0]
   for tri in sub['triangles']:
    for vi,ui in zip(tri[:3],tri[3:6]):
     p=positions[vi];assert all(math.isfinite(v) for v in p);uv=mesh['uvs'][ui] if mesh['uvs'] else [0,0];vertices.extend([*p,*uv]);allpoints.append(p)
   if vertices:batches.append({'object':o['key'],'mesh':refs[0],'material':refs[1],'selector':selector,'texture':dependencies['textures'][tex]['path'].replace('\\','/') if tex else None,'vertices':vertices})
 mode='sally-runtime-skin' if captured else 'sally-source-gao-world' if args.source_gao_world else 'sally-source-skin' if initial else 'sally-skin-diagnostic'
 out=ASSET_ROOT/'scenes'/mode/'scene.json';out.parent.mkdir(parents=True,exist_ok=True)
 scene={'name':'Sally · explicit skin diagnostic 7100B0E7','objects':len(selected),'preview_camera':{'target':[0.,0.8,0.],'distance':3.5},'batches':batches,'bounds':[[min(p[i] for p in allpoints) for i in range(3)],[max(p[i] for p in allpoints) for i in range(3)]],'limits':('Serialized initial actor skin matrix array. ' if initial else 'Diagnostic source/evaluated pose. ')+'Variant1 selected explicitly, identity actor/reference pose. Evaluated matrices supplied as no-scale6; native control VM and full palette writer not executed. No native visibility/material/shader parity.'}
 scene['name']='Sally · '+mode+' (unverified diagnostic)'
 scene['limits']='Diagnostic matrix source: '+mode+'. '+scene['limits'];out.write_text(json.dumps(scene))
 if captured:
  scene['limits']='Live actor-relative palette and selected variants. Unsynchronised read-only capture; offline source meshes, native render vertex buffers not yet compared. No animation evaluation/shader parity.'
  scene['runtime_snapshot']=str(args.runtime_snapshot);out.write_text(json.dumps(scene))
 report_path('stage4-'+mode+'-preview.json').write_text(json.dumps({'selected':selected,'scene':str(out),'batches':len(batches),'triangles':sum(len(b['vertices'])//15 for b in batches),'bounds':scene['bounds'],'limits':scene['limits']},indent=2));print(json.dumps({'scene':str(out),'parts':len(selected),'batches':len(batches),'bounds':scene['bounds']}))
if __name__=='__main__':main()
