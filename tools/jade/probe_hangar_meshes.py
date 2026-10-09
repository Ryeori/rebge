from project_paths import PROJECT_ROOT, report_path
import collections,json,struct
from bpak_reader import entries,decode
from jade_scene_probe import PATH
from jade_mesh import parse_mesh
def main():
    objects=json.load(open(report_path('hangar-object-probe.json')));index={e['name']:e for e in entries(PATH)}
    report=[];textures={};materials=set()
    with PATH.open('rb') as f:
        for key in sorted({d['key'] for o in objects for d in o['dependencies'] if d.get('kind')==1}):
            data=decode(f,index[key])
            try:
                mesh=parse_mesh(data)
                report.append({'key':key,'vertices':len(mesh['positions']),'triangles':sum(len(s['triangles']) for s in mesh['submeshes']),
                    'submeshes':len(mesh['submeshes']),'tail':mesh['trailing_size'],'mask':mesh['mask'],
                    'bounds':[[min(p[i] for p in mesh['positions']) for i in range(3)],[max(p[i] for p in mesh['positions']) for i in range(3)]]})
            except Exception as exc:report.append({'key':key,'error':str(exc)})
        def material(key):
            if key in materials or key not in index:return
            materials.add(key);data=decode(f,index[key]);kind,length=struct.unpack_from('<2I',data);pos=8+length
            if kind==4:
                count=struct.unpack_from('<I',data,pos)[0]
                for n in range(count):material(f'{struct.unpack_from("<I",data,pos+4+n*4)[0]:08X}')
            if kind==5:
                nxt=struct.unpack_from('<I',data,pos+24)[0];pos+=32
                while nxt:
                    nxt=struct.unpack_from('<H',data,pos)[0];tex=struct.unpack_from('<I',data,pos+16)[0];pos+=20
                    name=f'{tex:08X}'
                    if name in index:
                        payload=decode(f,index[name]);textures[name]={'size':len(payload),'prefix_hex':payload[:96].hex(),'footer_hex':payload[-32:].hex()}
        for o in objects:
            if len(o['visual_refs'])==2:material(o['visual_refs'][1])
    json.dump({'meshes':report,'materials':sorted(materials),'textures':textures},open(report_path('hangar-mesh-validation.json'),'w'),indent=2)
    print(json.dumps({'meshes':len(report),'parsed':sum('error' not in r for r in report),'errors':[r for r in report if 'error' in r],'textures':dict(list(textures.items())[:3])},indent=2))
if __name__=='__main__':main()
