from project_paths import PROJECT_ROOT, report_path
import json,pathlib,struct,collections
from bpak_reader import entries,decode
base=pathlib.Path(r'E:\SteamLibrary\steamapps\common\Beyond Good and Evil - 20th Anniversary Edition\Data\Paks')
mapping=json.load(open(report_path('jade-language-key-mapping.json')))['candidates']
for loc,file,idx in [('en','Text-en_US.pak',1),('ru','Text-ru.pak',11)]:
 es={e['name']:e for e in entries(base/file)};stats=collections.Counter();bad=[];samples=[]
 with (base/file).open('rb') as f:
  for g in mapping:
   r=g['records'][idx];txi=decode(f,es[r['first_key']]);txs=decode(f,es[r['second_key']]);stats['groups']+=1
   if len(txi)%68:bad.append({'group':g['resource'],'problem':'stride','length':len(txi)});continue
   offsets=[]
   for pos in range(0,len(txi),68):
    record=txi[pos:pos+68];offset=struct.unpack_from('<I',record)[0];offsets.append(offset);stats['records']+=1
    if offset>=len(txs):stats['outside']+=1
    else:
     end=txs.find(b'\0',offset)
     stats['unterminated']+=end<0
    name=record[4:].split(b'\0')[0];stats['names']+=bool(name)
   if len(samples)<3:samples.append({'group':g['resource'],'txi_bytes':len(txi),'txs_bytes':len(txs),'offsets':offsets[:8],'first_record_hex':txi[:68].hex()})
 print(loc,dict(stats),'bad',bad[:3],'samples',json.dumps(samples))
