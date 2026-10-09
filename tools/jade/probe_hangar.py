"""Confirmed GAO prefix and visual dependency probe for the home hangar."""
from project_paths import PROJECT_ROOT, report_path
import collections,json,struct,pathlib
from jade_scene_probe import PATH
from bpak_reader import entries,decode
def gao_prefix(data):
    if len(data)<126 or data[:4]!=b'.gao':raise ValueError('Invalid GAO prefix')
    version,unknown,flags=struct.unpack_from('<3I',data,4)
    # Native path consumes 2 legacy bytes then a 68-byte matrix, then BV marker.
    pos=96+4+(48 if flags&(1<<19) else 24)
    refs=[];visual_flags=0
    if flags&(1<<12) and flags&(1<<14):
        mesh,material,unknown2,mode,count=struct.unpack_from('<5I',data,pos)
        refs=[mesh,material];visual_flags=unknown2;pos+=20+count*4
        if pos>len(data): raise ValueError('Visual list exceeds GAO length')
    return {'version':version,'flags':f'{flags:08X}', 'matrix':struct.unpack_from('<16f',data,28),
            'visual_refs':[f'{k:08X}' for k in refs if k not in (0,0xffffffff)],
            'visual_flags':visual_flags,'visual_keys':[f'{k:08X}' for k in refs],'after_visual':pos}
def main():
    index={e['name']:e for e in entries(PATH)};out=[];types=collections.Counter()
    with PATH.open('rb') as f:
        listing=decode(f,index['D90057EF'])
        for offset in range(0,len(listing),8):
            key,tag=struct.unpack_from('<I4s',listing,offset)
            if tag!=b'.gao':raise ValueError('Unexpected world list tag')
            name=f'{key:08X}';data=decode(f,index[name]);item=dict(key=name,**gao_prefix(data))
            deps=[]
            for ref in item['visual_refs']:
                if ref not in index: deps.append({'key':ref,'missing':True});continue
                payload=decode(f,index[ref]);kind=struct.unpack_from('<I',payload)[0];types[kind]+=1
                deps.append({'key':ref,'size':len(payload),'kind':kind,'prefix_hex':payload[:96].hex()})
            item['dependencies']=deps;out.append(item)
    pathlib.Path(report_path('hangar-object-probe.json')).write_text(json.dumps(out,indent=2))
    print('objects',len(out),'visual',sum(bool(x['visual_refs']) for x in out),'dependency types',types)
    print(json.dumps([x for x in out if x['visual_refs']][:3],indent=2))
if __name__=='__main__':main()
