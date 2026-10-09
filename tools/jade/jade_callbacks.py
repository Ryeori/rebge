"""Recover named callback metadata from the user's PE; layout confirmed through Ghidra MCP."""
from project_paths import PROJECT_ROOT, report_path
import argparse, json, mmap, re, struct
from pathlib import Path

def discover(path):
    with path.open('rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as data:
        pe=struct.unpack_from('<I',data,0x3c)[0]
        if data[pe:pe+4]!=b'PE\0\0': raise ValueError('Not PE')
        count=struct.unpack_from('<H',data,pe+6)[0]
        optional=pe+24; size=struct.unpack_from('<H',data,pe+20)[0]
        if struct.unpack_from('<H',data,optional)[0]!=0x20b: raise ValueError('Requires PE32+')
        base=struct.unpack_from('<Q',data,optional+24)[0]
        sections=[]
        for i in range(count):
            p=optional+size+i*40
            name=data[p:p+8].rstrip(b'\0').decode('ascii')
            virtual_size,rva,raw_size,raw_offset=struct.unpack_from('<4I',data,p+8)
            flags=struct.unpack_from('<I',data,p+36)[0]
            if raw_offset+raw_size>len(data): raise ValueError('Section exceeds file')
            sections.append((name,rva,raw_offset,raw_size,virtual_size,flags))
        strings=[]
        for name,rva,offset,length,_,flags in sections:
            if flags&0x20000000: continue
            payload=data[offset:offset+length]
            for match in re.finditer(rb'(?<![A-Za-z0-9_])[A-Za-z][A-Za-z0-9_]{4,119}\x00',payload):
                strings.append((match.group()[:-1].decode(),base+rva+match.start()))
        callbacks=[]
        executable=[(base+rva,base+rva+max(vs,length)) for _,rva,_,length,vs,flags in sections if flags&0x20000000]
        names={pointer:name for name,pointer in strings}
        for section,rva,offset,length,_,flags in sections:
            if flags&0x20000000: continue
            key=name_ptr=0
            for i,(callback,) in enumerate(struct.iter_unpack('<Q',data[offset:offset+length-length%8])):
                if name_ptr in names and key<=0xffffffff and any(lo<=callback<hi for lo,hi in executable):
                    target=callback; chain=[]
                    for _ in range(8):
                        location=next((raw+target-base-va for _,va,raw,n,_,fl in sections if base+va<=target<base+va+n),None)
                        if location is None or data[location]!=0xe9: break
                        destination=target+5+struct.unpack_from('<i',data,location+1)[0]
                        if destination in chain or not any(lo<=destination<hi for lo,hi in executable): break
                        chain.append(target);target=destination
                    callbacks.append(dict(name=names[name_ptr],key=f'{key:08X}',string_address=f'{name_ptr:x}',record_address=f'{base+rva+(i-2)*8:x}',callback=f'{callback:x}',resolved_callback=f'{target:x}',direct_jump_chain=[f'{v:x}' for v in chain]))
                key,name_ptr=name_ptr,callback
        return dict(image_base=f'{base:x}',layout='uint64 key/name pointer/callback; Ghidra verified',callbacks=callbacks)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,default=Path(r'E:\SteamLibrary\steamapps\common\Beyond Good and Evil - 20th Anniversary Edition\bge.exe'));p.add_argument('--output',type=Path,default=Path(report_path('stage4-native-callbacks.json')));args=p.parse_args()
    result=discover(args.exe);args.output.write_text(json.dumps(result,indent=2),encoding='utf8')
    print(f"Recovered {len(result['callbacks'])} named callbacks; metadata only: {args.output}")
    for row in result['callbacks']:
        if re.search('Jade.*(move|jump|saut|init)|(?:avatar|perso|mainchar|hero).*|camera_derriere_cd_',row['name'],re.I): print(row['name'],row['key'],row['callback'])
