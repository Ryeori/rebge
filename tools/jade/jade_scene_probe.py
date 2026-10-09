"""Read-only WOW inventory and confirmed fixed header fields."""
from project_paths import PROJECT_ROOT, report_path
import hashlib, json, pathlib, struct
from bpak_reader import entries,decode
PATH=pathlib.Path(r'E:\SteamLibrary\steamapps\common\Beyond Good and Evil - 20th Anniversary Edition\Data\Paks\Resources.pak')
def main():
    index={e['name']:e for e in entries(PATH)}; worlds=[]
    with PATH.open('rb') as f:
        for e in index.values():
            if e['unpacked']!=228: continue
            data=decode(f,e)
            if data[:4]!=b'.wow': continue
            refs=struct.unpack_from('<5I',data,208)
            dependencies=[]
            for slot,key in enumerate(refs):
                target=index.get(f'{key:08X}')
                item={'slot':slot,'key':f'{key:08X}','present':target is not None}
                if target:
                    payload=decode(f,target)
                    item.update(size=len(payload),prefix_hex=payload[:80].hex())
                dependencies.append(item)
            worlds.append({'key':e['name'],'name':data[16:80].split(b'\0')[0].decode('cp1252'),
                'version':struct.unpack_from('<I',data,4)[0], 'sha256':hashlib.sha256(data).hexdigest(),
                'matrix_float32':struct.unpack_from('<16f',data,80),'dependencies':dependencies})
    pathlib.Path(report_path('jade-world-inventory.json')).write_text(json.dumps(worlds,indent=2))
    print('Worlds',len(worlds))
    for w in worlds:
        if any(s in w['name'].lower() for s in ('phare','lighthouse','main','island','ilot')): print(w['key'],w['name'],w['dependencies'])
if __name__=='__main__':main()
