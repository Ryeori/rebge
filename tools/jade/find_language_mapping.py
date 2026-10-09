from project_paths import PROJECT_ROOT, report_path
import json,pathlib,struct,collections
from bpak_reader import entries,decode
base=pathlib.Path(r'E:\SteamLibrary\steamapps\common\Beyond Good and Evil - 20th Anniversary Edition\Data\Paks')
keys={loc:{int(e['name'],16) for e in entries(base/file) if e['kind']==1} for loc,file in [('en','Text-en_US.pak'),('ru','Text-ru.pak')]}
hits=[];scanned=0;errors=0
with (base/'Resources.pak').open('rb') as f:
 for e in entries(base/'Resources.pak'):
  if not 16<=e['unpacked']<=4096:continue
  try:d=decode(f,e)
  except Exception:errors+=1;continue
  scanned+=1
  en=[];ru=[]
  for pos in range(0,len(d)-3,4):
   k=struct.unpack_from('<I',d,pos)[0]
   if k in keys['en']:en.append((pos,f'{k:08X}'))
   if k in keys['ru']:ru.append((pos,f'{k:08X}'))
  if en and ru:
   row={'resource':e['name'],'bytes':len(d),'en_matches':en,'ru_matches':ru,'records':[]}
   if len(d)%16==0 and len(d)<=208:
    row['records']=[{'language_index':i//16,'first_key':f'{struct.unpack_from("<I",d,i)[0]:08X}','first_marker':d[i+4:i+8].hex(),'second_key':f'{struct.unpack_from("<I",d,i+8)[0]:08X}','second_marker':d[i+12:i+16].hex()} for i in range(0,len(d),16)]
   hits.append(row)
result={'scanned_small_resources':scanned,'decode_errors':errors,'candidate_count':len(hits),'candidates':hits}
pathlib.Path(report_path('jade-language-key-mapping.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print('scanned',scanned,'errors',errors,'candidates',len(hits))
for row in hits[:3]:print(json.dumps(row))
