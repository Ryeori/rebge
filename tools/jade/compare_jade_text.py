"""Compare decoded text archive resources to legacy JadeStudio container framing."""
from project_paths import PROJECT_ROOT, report_path
import collections,json,pathlib,re,struct
from bpak_reader import entries,decode
base=pathlib.Path(r'E:\SteamLibrary\steamapps\common\Beyond Good and Evil - 20th Anniversary Edition\Data\Paks')
def legacy_container(data):
    pos=0;groups=0
    def u32():
        nonlocal pos
        v=struct.unpack_from('<I',data,pos)[0];pos+=4;return v
    def take(n):
        nonlocal pos
        if n>len(data)-pos:raise ValueError('length out of bounds')
        b=data[pos:pos+n];pos+=n;return b
    try:
        if not data:return False
        while pos<len(data):
            n=u32()
            if n%8 or n>len(data)-pos:return False
            count=n//8;table=take(n)
            if any(table[i*8+4:i*8+8]!=b'.txg' for i in range(count)):return False
            for i in range(count):
                m=u32()
                if m%16:return False
                table=take(m)
                if any(table[j+4:j+8]!=b'.txi' or table[j+12:j+16]!=b'.txs' for j in range(0,m,16)):return False
                u32()
            for i in range(count):
                n=u32()
                if n%4:return False
                take(n);take(u32())
            groups+=count
        return groups>0
    except (ValueError,struct.error):return False
reports=[];keysets=[]
for name in ['Text-en_US.pak','Text-ru.pak']:
    stats=collections.Counter();keys=set();examples=[]
    with (base/name).open('rb') as f:
        for e in entries(base/name):
            d=decode(f,e);keys.add(e['name']);stats['resources']+=1
            stats['empty']+=not d;stats['leading_zero_u32']+=d.startswith(b'\0'*4)
            stats['unicode_escape_resources']+=bool(re.search(rb'\\[Uu]\+\d+',d))
            stats['legacy_container_matches']+=legacy_container(d)
            for tag in (b'.txg',b'.txi',b'.txs'):stats[tag.decode()+'_resources']+=tag in d
            if len(examples)<6:examples.append({'key':e['name'],'bytes':len(d),'legacy_container':legacy_container(d),'unicode_escapes':len(re.findall(rb'\\[Uu]\+\d+',d))})
    reports.append({'archive':name,'statistics':dict(stats),'examples':examples});keysets.append(keys)
result={'archives':reports,'shared_resource_keys':len(keysets[0]&keysets[1]),'interpretation':'Legacy aggregate TextFile framing is tested strictly; a negative result does not exclude reusable txi/txs inner layouts. No dialogue strings exported.'}
pathlib.Path(report_path('jade-text-comparison.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
