"""Compare captured native palette and source mesh vertices, without claiming frame parity."""
import json,argparse,math
from pathlib import Path
from jade_animation_root import rigid_inverse
from jade_pose import affine_product
from project_paths import ASSET_ROOT,report_path

def main():
 p=argparse.ArgumentParser();p.add_argument('snapshot',type=Path);a=p.parse_args();live=json.loads(a.snapshot.read_text())
 inverse=rigid_inverse(live['actor']['world_matrix'][:16]);palette=live['palette']['matrices'];objects=live['objects']
 variants=json.loads(report_path('stage4-sally-variant-geometry.json').read_text());source={o['key']:o for o in variants['objects']};rows=[]
 for link in variants['links']:
  slot=link['slot']
  if link['variant']!=live['selected_variants'][slot]:continue
  key=source[link['gao']]['gao'].get('visual_keys',[None])[0]
  path=ASSET_ROOT/'models/meshes'/('sally-'+str(key)+'.json')
  if not path.exists():continue
  offline=json.loads(path.read_text())['positions'];native=objects[slot].get('geometry_positions',[])
  n=min(len(offline),len(native));delta=max((abs(offline[i][c]-native[i][c]) for i in range(n) for c in range(3)),default=None)
  source_positions={tuple(v) for v in offline};native_positions={tuple(v) for v in native}
  rows.append({'slot':slot,'variant':link['variant'],'gao':link['gao'],'mesh':key,'source_vertices':len(offline),'native_vertices':len(native),'compared_prefix_vertices':n,'prefix_max_abs_error':delta,'exact_vertex_count':len(offline)==len(native),'all_native_positions_in_source':bool(native) and native_positions<=source_positions,'all_source_positions_in_native':bool(native) and source_positions<=native_positions,'unique_native_positions':len(native_positions),'native_duplicates':len(native)-len(native_positions)})
 errors=[]
 for o in objects:
  if 'matrix' not in o:continue
  expected=affine_product(o['matrix'],inverse);actual=palette[o['slot']]['matrix']
  errors.append({'slot':o['slot'],'max_abs_error':max(abs(expected[i]-actual[i]) for i in range(16))})
 result={'snapshot':str(a.snapshot),'geometry':rows,'actor_relative_palette':errors,'max_palette_error':max(r['max_abs_error'] for r in errors),'limits':['Unsynchronised native reads; world and palette may belong to different evaluation times.','Vertex prefix agreement does not prove topology, material or full shader parity.']}
 out=report_path('stage4-sally-runtime-verification.json');out.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
