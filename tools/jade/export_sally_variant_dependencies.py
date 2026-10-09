"""Export native-linked Sally variant materials/textures and skin bindings."""
import json,struct,hashlib,collections
from pathlib import Path
from bpak_reader import entries,decode
from jade_scene_probe import PATH
from jade_mesh import Cursor
from jade_skin import decode_skin_word
from jade_texture import color_image
from project_paths import ASSET_ROOT,report_path

def main():
 report=json.loads(report_path('stage4-sally-variant-geometry.json').read_text());idx={e['name']:e for e in entries(PATH)};materials={};textures={};skins=[];unsupported=[]
 with PATH.open('rb') as f:
  def load(key):return decode(f,idx[key])
  def material(key,seen=()):
   if key in materials:return
   if key in seen:raise ValueError('Material cycle')
   raw=load(key);c=Cursor(raw);kind=c.read('I');c.skip(c.read('I'));row={'kind':kind,'source_sha256':hashlib.sha256(raw).hexdigest()}
   if kind==4:
    n=c.read('I');assert n<=256;refs=[f'{c.read("I"):08X}' for _ in range(n)];row['materials']=refs
    for ref in refs:material(ref,seen+(key,))
   elif kind==5:
    words=list(c.read('8I'));nxt=words[6];layers=[]
    while nxt:
     if len(layers)>64:raise ValueError('Too many material layers')
     off=c.pos;segment=raw[off:off+20];assert len(segment)==20;nxt=struct.unpack_from('<H',segment)[0];tex=f'{struct.unpack_from("<I",segment,16)[0]:08X}';c.skip(20);layers.append({'texture':tex,'source_hex':segment.hex()})
     if tex not in textures:
      try:
       payload=load(tex);info,image=color_image(payload);out=ASSET_ROOT/'textures'/('sally-'+tex+'.png');image.save(out);textures[tex]={'path':str(out.relative_to(ASSET_ROOT)),'source_sha256':hashlib.sha256(payload).hexdigest(),'export_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'size':image.size}
      except (ValueError,NotImplementedError,KeyError) as e:unsupported.append({'texture':tex,'reason':str(e)});textures[tex]={'unsupported':str(e)}
    row.update(words_u32=words,layers=layers)
   else:row['unsupported']='Material kind unresolved'
   row['trailing_hex']=raw[c.pos:].hex();out=ASSET_ROOT/'materials'/('sally-'+key+'.json');out.write_text(json.dumps(row,indent=2));materials[key]={'path':str(out.relative_to(ASSET_ROOT)),**row}
  for o in report['objects']:
   g=o.get('gao',{});keys=g.get('visual_keys',[])
   if len(keys)==2 and keys[1] not in ('FFFFFFFF','00000000'):material(keys[1])
   flags=int(g['flags'],16);array=o.get('pre_action_array')
   if not array or array['stride']!=8:continue
   raw=load(o['key']);c=Cursor(raw);c.pos=g['after_visual']
   if flags&0x400000:c.skip(72)
   if flags&2:c.skip(16)
   n=c.read('I');assert n==array['count'];bindings=[]
   for i in range(n):
    ref,slot=c.read('2I');bindings.append({'skin_index':i,'actor_key':f'{ref:08X}','matrix_index':slot})
   geometry=keys[0] if keys else None;path=ASSET_ROOT/'models/meshes'/('sally-'+str(geometry)+'.json');ext=json.loads(path.read_text()).get('extended_header') if path.exists() else None
   influences=[]
   if ext:
    mesh=json.loads(path.read_text());counts=collections.Counter();sums=collections.defaultdict(float)
    for record in ext['records']:
     assert record['index_u16']<n
     decoded=[decode_skin_word(w) for w in record['words_u32']]
     for v in decoded:assert v['vertex']<len(mesh['positions']);counts[v['vertex']]+=1;sums[v['vertex']]+=v['weight']
     influences.append({'skin_index':record['index_u16'],'bind_matrix':record['matrix'],'bind_flags':record['matrix_flags'],'influences':decoded})
    stats={'covered_vertices':len(counts),'vertices':len(mesh['positions']),'max_influences':max(counts.values(),default=0),'weight_sum_range':[min(sums.values(),default=0),max(sums.values(),default=0)]}
   else:stats={}
   skins.append({'gao':o['key'],'geometry':geometry,'bindings':bindings,'influence_records':influences,'stats':stats})
 result={'schema':'jade-sally-variant-dependencies-v1','materials':materials,'textures':textures,'skins':skins,'unsupported':unsupported,'limits':'Source skin entries and weights confirmed. Runtime matrix composition/variant selection explicit, no live parity. PNG first color stream only; material words unclassified.'}
 out=ASSET_ROOT/'skeletons/sally/visual-skin-bindings.json';out.write_text(json.dumps(result,indent=2));report_path('stage4-sally-variant-dependencies.json').write_text(json.dumps(result,indent=2));print(json.dumps({'materials':len(materials),'textures':len(textures),'skin_entries':len(skins),'unsupported':unsupported}))
if __name__=='__main__':main()
