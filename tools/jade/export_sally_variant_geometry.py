import sys,json,struct,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from probe_character_resources import inspect_keys
from bpak_reader import entries,decode
from jade_scene_probe import PATH
from jade_mesh import parse_mesh
from project_paths import report_path,ASSET_ROOT
r=json.loads(report_path('stage4-sally-visual-variants-probe.json').read_text());links=[]
for group in r:
 for listing in group['lists']:
  raw=bytes.fromhex(listing['hex']);assert len(raw)==listing['size'] and len(raw)%8==0
  for variant,(key,tag) in enumerate(struct.iter_unpack('<I4s',raw)):
   assert tag==b'.gao';links.append({'slot':group['slot'],'variant':variant,'gao':f'{key:08X}'})
objects=inspect_keys(sorted(set(x['gao'] for x in links)));idx={e['name']:e for e in entries(PATH)};geometry=[]
with PATH.open('rb') as f:
 for o in objects:
  key=(o.get('gao',{}).get('visual_keys') or ['FFFFFFFF'])[0]
  if key not in idx or any(m['key']==key for m in geometry):continue
  raw=decode(f,idx[key]);row={'key':key,'source_sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw),'kind':struct.unpack_from('<I',raw)[0]}
  try:
   mesh=parse_mesh(raw);row.update(vertices=len(mesh['positions']),triangles=sum(len(s['triangles']) for s in mesh['submeshes']),trailing_size=mesh['trailing_size'])
   target=ASSET_ROOT/'models/meshes'/('sally-'+key+'.json');target.write_text(json.dumps({k:v for k,v in mesh.items() if k!='cursor'},indent=2,default=str));row['export_path']=str(target.relative_to(ASSET_ROOT))
  except (ValueError,NotImplementedError,struct.error) as e:row['unsupported']=str(e)
  geometry.append(row)
report_path('stage4-sally-variant-geometry.json').write_text(json.dumps({'links':links,'objects':objects,'geometry':geometry,'limits':'Native-linked visual variant candidates. Mesh exports static source coordinates; skinning not applied, runtime variant choice explicit.'},indent=2));print(json.dumps({'variants':len(links),'geometry':geometry},indent=2))

