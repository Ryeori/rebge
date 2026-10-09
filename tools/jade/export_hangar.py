"""Static home-hangar slice, exported privately from the user's Resources.pak."""
from project_paths import PROJECT_ROOT, report_path
import argparse,collections,hashlib,json,pathlib,struct
from bpak_reader import entries,decode
from jade_scene_probe import PATH
from probe_hangar import gao_prefix
from jade_mesh import parse_mesh
from jade_texture import color_image
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    root=pathlib.Path(args.output).resolve();workspace=PROJECT_ROOT
    if not root.is_relative_to(workspace) or root==workspace or root.is_relative_to(PATH.parents[2]):raise ValueError('Output must be a project subdirectory, outside the game installation')
    root.mkdir(parents=True,exist_ok=True);(root/'textures').mkdir(exist_ok=True)
    index={e['name']:e for e in entries(PATH)};report={'scene':'D90057F0','name':'00_01_home_sas_hangar','unsupported':[],'textures':{},'meshes':{},'materials':{}}
    mesh_cache={};mat_cache={};tex_cache={};batches=[];bounds=[]
    with PATH.open('rb') as f:
        def load(key):
            if key not in index:raise ValueError(f'Missing resource {key}')
            return decode(f,index[key])
        def texture(key):
            if key in tex_cache:return tex_cache[key]
            tex_cache[key]=None
            try:
                data=load(key);info,im=color_image(data)
                # Preview uses at most 1024px; original BC streams remain available through the converter.
                im.thumbnail((1024,1024));im.save(root/'textures'/f'{key}.png')
                report['textures'][key]={k:v for k,v in info.items() if k not in ('streams','extension')}
                tex_cache[key]=f'textures/{key}.png'
            except Exception as exc:report['unsupported'].append({'type':'texture','key':key,'reason':str(exc)})
            return tex_cache[key]
        def material(key,seen=None):
            if key in mat_cache:return mat_cache[key]
            seen=set() if seen is None else seen
            if key in seen:raise ValueError('Material reference cycle')
            seen.add(key);data=load(key);kind,length=struct.unpack_from('<2I',data);pos=8+length;result=[]
            if kind==4:
                n=struct.unpack_from('<I',data,pos)[0]
                if n>256 or pos+4+n*4>len(data):raise ValueError('Invalid material list')
                for i in range(n):result.extend(material(f'{struct.unpack_from("<I",data,pos+4+i*4)[0]:08X}',seen.copy()))
            elif kind==5:
                nxt=struct.unpack_from('<I',data,pos+24)[0];pos+=32;layers=[]
                while nxt:
                    if pos+20>len(data):raise ValueError('Truncated material layer')
                    nxt=struct.unpack_from('<H',data,pos)[0];tex=struct.unpack_from('<I',data,pos+16)[0];pos+=20
                    layers.append(f'{tex:08X}')
                result=[texture(layers[0]) if layers else None]
                report['materials'][key]={'kind':kind,'layers':layers,'preview_layer':0}
            else:
                report['unsupported'].append({'type':'material','key':key,'kind':kind});result=[None]
            mat_cache[key]=result;return result
        def geometry(key,seen=None):
            if key in mesh_cache:return mesh_cache[key]
            seen=set() if seen is None else seen
            if key in seen:raise ValueError('Geometry reference cycle')
            seen.add(key);data=load(key);kind,length=struct.unpack_from('<2I',data);pos=8+length
            if kind==8:
                count=data[pos];pos+=8
                if count>6 or pos+max(1,count)*4>len(data):raise ValueError('Invalid LOD list')
                keys=[f'{struct.unpack_from("<I",data,pos+i*4)[0]:08X}' for i in range(max(1,count))]
                choices=[k for k in keys if k not in ('00000000','FFFFFFFF')]
                if not choices:return []
                result=geometry(choices[0],seen);report['meshes'][key]={'kind':8,'lod_keys':keys,'chosen':choices[0]}
            elif kind==1:
                mesh=parse_mesh(data);result=[(key,mesh)]
                report['meshes'][key]={'kind':1,'vertices':len(mesh['positions']),'triangles':sum(len(s['triangles']) for s in mesh['submeshes']),
                    'tail_bytes':mesh['trailing_size'],'roundtrip':True,'sha256':hashlib.sha256(data).hexdigest()}
            else:raise NotImplementedError(f'Geometry kind {kind}')
            mesh_cache[key]=result;return result
        listing=load('D90057EF');objects=[]
        for offset in range(0,len(listing),8):
            key,tag=struct.unpack_from('<I4s',listing,offset)
            if tag!=b'.gao':raise ValueError('Invalid GAO list')
            name=f'{key:08X}';obj=gao_prefix(load(name));objects.append({'key':name,**obj})
            if len(obj['visual_keys'])!=2:continue
            geo,mat=obj['visual_keys'];m=obj['matrix']
            if geo in ('00000000','FFFFFFFF'):continue
            try:
                materials=material(mat) if mat not in ('00000000','FFFFFFFF') else [None];meshes=geometry(geo)
                for mesh_key,mesh in meshes:
                    for sub in mesh['submeshes']:
                        data=[];selector=sub['unknown'];uri=materials[selector] if selector<len(materials) else materials[0] if materials else None
                        for triangle in sub['triangles']:
                            for vi,ui in zip(triangle[:3],triangle[3:6]):
                                p=mesh['positions'][vi];world=[sum(p[j]*m[j*4+i] for j in range(3))+m[12+i] for i in range(3)]
                                uv=mesh['uvs'][ui] if mesh['uvs'] else (0,0)
                                data.extend([*world,*uv]);bounds.append(world)
                        if data:batches.append({'object':name,'mesh':mesh_key,'material':mat,'selector':selector,'texture':uri,'vertices':data})
            except Exception as exc:report['unsupported'].append({'type':'object','key':name,'reason':str(exc)})
    scene={'name':report['name'],'batches':batches,'bounds':[[min(p[i] for p in bounds) for i in range(3)],[max(p[i] for p in bounds) for i in range(3)]],
        'coordinate_system':'Jade source axes; Z-up display provisional; no rescaling','objects':len(objects)}
    (root/'scene.json').write_text(json.dumps(scene,separators=(',',':')))
    report.update(objects=len(objects),batches=len(batches),rendered_objects=len({b['object'] for b in batches}),triangles=sum(len(b['vertices'])//15 for b in batches),bounds=scene['bounds'],output=str(root))
    report['limitations']=['Static snapshot, no gameplay/animation/effect simulation','First texture layer only; material selector interpretation provisional',
        'Z-up and source-unit scale are provisional until compared with an original frame','Mesh tail and texture auxiliary streams retained only by source reader; preview does not apply them']
    (root/'validation.json').write_text(json.dumps(report,indent=2));pathlib.Path(report_path('hangar-export-validation.json')).write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k] for k in ('output','objects','rendered_objects','batches','triangles','bounds','unsupported')},indent=2))
if __name__=='__main__':main()
