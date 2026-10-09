from project_paths import PROJECT_ROOT, report_path
import struct,json,pathlib
base=pathlib.Path(r'E:\SteamLibrary\steamapps\common\Beyond Good and Evil - 20th Anniversary Edition\Data\Paks')
results=[]
for path in sorted(base.glob('*.pak')):
    row={'file':path.name,'size':path.stat().st_size}
    try:
        with path.open('rb') as f:
            h=f.read(24)
            magic,word4,priority,flag,count,index_size=struct.unpack('<4s5I',h)
            if magic!=b'BPAK': raise ValueError('unexpected magic')
            if index_size>path.stat().st_size-24: raise ValueError('index out of bounds')
            f.seek(-index_size,2); table=f.read(index_size)
        pos=0; named=0; keyed=0; examples=[]; invalid_ranges=0; compressed_entries=0
        for i in range(count):
            kind=table[pos];pos+=1
            if kind==0:
                n=struct.unpack_from('<I',table,pos)[0];pos+=4
                if n>len(table)-pos: raise ValueError('name out of bounds')
                pos+=n;named+=1
            else:
                key=struct.unpack_from('<I',table,pos)[0];pos+=4;keyed+=1
            values=struct.unpack_from('<6I',table,pos);pos+=24
            unpacked,packed,unknown,relative_offset=struct.unpack('<IIQQ',struct.pack('<6I',*values))
            stored=packed or unpacked; offset=relative_offset+24
            if offset<24 or offset+stored>row['size']-index_size: invalid_ranges+=1
            if packed: compressed_entries+=1
            if len(examples)<2:examples.append({'kind':kind,'raw_metadata_u32':values})
        row.update(word4=word4,priority=priority,flag=flag,entry_count=count,index_size=index_size,parsed_bytes=pos,named_entries=named,keyed_entries=keyed,exact_consumption=pos==index_size,metadata_examples=examples,invalid_payload_ranges=invalid_ranges,compressed_entries=compressed_entries)
    except Exception as e:row['error']=str(e)
    results.append(row)
pathlib.Path(report_path('pak-index-validation.json')).write_text(json.dumps(results,indent=2),encoding='utf-8')
for r in results:print(r['file'], 'entries=',r.get('entry_count'),'index=',r.get('index_size'),'exact=',r.get('exact_consumption'),'error=',r.get('error'))

