"""Restricted Wwise v140 event/action/source links; remaining payloads opaque."""
import json,struct,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def event_ids(data):
 pos=0;n=0
 while True:
  if pos>=len(data) or pos>=10:raise ValueError('Invalid event count')
  b=data[pos];pos+=1;n=(n<<7)|(b&127)
  if not b&128:break
 if len(data)!=pos+n*4:raise ValueError('Event size mismatch')
 return list(struct.unpack_from('<'+'I'*n,data,pos))
def main():
 banks=json.loads((ROOT/'reports/jade/stage4-wwise-bank-structure.json').read_text())['banks'];out=[];totals=collections.Counter()
 for bank in banks:
  objs={o['id']:o for o in bank['objects']};assert len(objs)==len(bank['objects'])
  events=[];actions=[];sounds=[];media={m['media_id']:m for m in bank['media']}
  for o in objs.values():
   d=bytes.fromhex(o['payload_hex'])
   if o['type']==4:
    ids=event_ids(d);assert all(i in objs and objs[i]['type']==3 for i in ids)
    events.append({'id':o['id'],'action_ids':ids});totals['event_action_edges']+=len(ids)
   elif o['type']==3:
    if len(d)<7:raise ValueError('Truncated action')
    kind,target,bus=struct.unpack_from('<HIB',d);typ=objs.get(target,{}).get('type')
    actions.append({'id':o['id'],'action_type':kind,'target_id':target,'is_bus':bool(bus&1),'target_type_in_bank':typ,'unparsed_tail_hex':d[7:].hex()})
    if kind==0x0403:totals['play_actions']+=1;totals['play_target_resolved']+=typ is not None;totals['direct_sound_plays']+=typ==2
   elif o['type']==2:
    if len(d)<14:raise ValueError('Truncated sound source')
    plugin,stream,source,size,bits=struct.unpack_from('<IBIIB',d)
    sounds.append({'id':o['id'],'plugin_id':plugin,'stream_type':stream,'source_id':source,'in_memory_media_size':size,'source_bits':bits,'media_in_bank':source in media,'unparsed_tail_hex':d[14:].hex()})
    totals['sounds']+=1;totals['sound_source_in_bank']+=source in media
  totals['events']+=len(events);totals['actions']+=len(actions)
  out.append({'bank':bank['path'],'events':events,'actions':actions,'sounds':sounds})
 result={'bank_version':140,'format_sources':['https://github.com/bnnm/wwiser/blob/master/wwiser/parser/wparser.py','https://github.com/bnnm/wwiser/blob/master/wwiser/parser/wmodel.py','https://github.com/bnnm/wwiser/blob/master/wwiser/parser/wdefs.py'],'banks':out,'counts':dict(totals),'limits':'Prefix fields only. Containers/music/playlists, action properties/timing, bus/global targets and language selection unresolved. Numeric IDs are not original names. No runtime playback parity.'}
 (ROOT/'reports/jade/stage4-wwise-event-links.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(totals))
if __name__=='__main__':main()
