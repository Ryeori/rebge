import struct,json
from bpak_reader import entries,decode
from jade_scene_probe import PATH
from probe_hangar import gao_prefix
from jade_mesh import Cursor
from project_paths import report_path
idx={e['name']:e for e in entries(PATH)}
with PATH.open('rb') as f:raw=decode(f,idx['71003F5A'])
p=gao_prefix(raw);flags=int(p['flags'],16);c=Cursor(raw);c.pos=p['after_visual']
if flags&0x400000:c.skip(72)
if flags&2:c.skip(16)
n=c.read('I');assert n==47 and not flags&0x1000000
mats=[]
for i in range(n):m=list(c.read('16f'));mf=c.read('I');c.skip(64);mats.append({'slot':i,'matrix':m,'flags':mf})
report_path('stage4-sally-source-skin-matrices.json').write_text(json.dumps({'actor':'71003F5A','matrices':mats,'limits':'Serialized initial matrix array, not live animated pose.'},indent=2));print(n)
