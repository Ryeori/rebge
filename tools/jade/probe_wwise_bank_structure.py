"""Validate bank object framing and distinguish full/prefetch embedded RIFF media."""
import json,struct,hashlib,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def chunks(data):
 pos=0
 while pos<len(data):
  if pos+8>len(data):raise ValueError('Truncated chunk header')
  tag,n=struct.unpack_from('<4sI',data,pos)
  if pos+8+n>len(data):raise ValueError('Truncated bank chunk')
  yield tag,data[pos+8:pos+8+n]
  pos+=8+n

def hirc_objects(data):
 if len(data)<4:raise ValueError('Missing HIRC count')
 count=struct.unpack_from('<I',data)[0];pos=4;out=[]
 for _ in range(count):
  if pos+5>len(data):raise ValueError('Truncated HIRC object header')
  kind,n=struct.unpack_from('<BI',data,pos);pos+=5
  if n<4 or pos+n>len(data):raise ValueError('Invalid HIRC object size')
  obj=data[pos:pos+n];out.append({'type':kind,'id':struct.unpack_from('<I',obj)[0],'size':n,'payload_hex':obj[4:].hex()});pos+=n
 if pos!=len(data):raise ValueError('HIRC trailing bytes')
 return out

def main():
 source=json.loads((ROOT/'reports/jade/stage4-wwise-audio-source-export.json').read_text())['resources']
 streams=collections.defaultdict(list)
 for r in source:
  if 'format' in r:streams[Path(r['path']).stem].append(r)
 banks=[];status=collections.Counter()
 for r in source:
  if 'embedded_media' not in r:continue
  data=(ROOT/'assets'/r['path']).read_bytes(); media=[]
  for m in r['embedded_media']:
   raw=data[m['offset']:m['offset']+m['size']];assert hashlib.sha256(raw).hexdigest()==m['sha256']
   row=dict(m)
   if len(raw)>=12 and raw[:4]==b'RIFF' and raw[8:12]==b'WAVE':
    declared=struct.unpack_from('<I',raw,4)[0]+8
    row['declared_riff_size']=declared;row['status']='complete' if declared==len(raw) else ('prefetch' if declared>len(raw) else 'trailing_bytes')
   else:row['status']='non_riff'
   candidates=streams.get(str(m['media_id']),[]);matches=[]
   for candidate in candidates:
    with (ROOT/'assets'/candidate['path']).open('rb') as f:prefix=f.read(len(raw))
    if prefix==raw:matches.append(candidate['path'])
   row['exact_stream_prefix_matches']=matches;status[row['status']]+=1;media.append(row)
  objs=[]
  for tag,payload in chunks(data):
   if tag==b'HIRC':objs=hirc_objects(payload)
  banks.append({'path':r['path'],'objects':objs,'object_type_counts':dict(collections.Counter(str(o['type']) for o in objs)),'media':media})
 out={'schema':'wwise-bank-structure-v1','banks':banks,'media_status_counts':dict(status),'limits':'HIRC framing and raw payloads only; type-specific fields/event links unparsed. Prefix comparison exact bytes, not inferred playable stream.'}
 (ROOT/'reports/jade/stage4-wwise-bank-structure.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
 print(json.dumps({'banks':len(banks),'objects':sum(len(b['objects']) for b in banks),'media':dict(status),'matched_prefixes':sum(bool(m['exact_stream_prefix_matches']) for b in banks for m in b['media'])}))
if __name__=='__main__':main()
