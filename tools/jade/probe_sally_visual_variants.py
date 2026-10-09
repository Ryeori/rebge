import sys,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/jade'))
from bpak_reader import entries,decode
from jade_scene_probe import PATH
idx={e['name']:e for e in entries(PATH)};parts=json.loads((ROOT/'reports/jade/stage4-sally-all-parts.json').read_text());out=[]
with PATH.open('rb') as f:
 for slot,o in enumerate(parts['objects']):
  key=o.get('visual_variant_descriptor')
  if not key:continue
  raw=decode(f,idx[key]); row={'slot':slot,'gao':o['key'],'descriptor':key,'hex':raw.hex(),'size':len(raw)}
  if len(raw) in (8,16):
   refs=struct.unpack_from('<II',raw);row['keys']=[f'{v:08X}' for v in refs];row['lists']=[]
   for ref in row['keys']:
    if ref not in idx:continue
    d=decode(f,idx[ref]);row['lists'].append({'key':ref,'size':len(d),'hex':d.hex()[:4000]})
  out.append(row)
(ROOT/'reports/jade/stage4-sally-visual-variants-probe.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2)[:8000])

