import json,subprocess,xml.etree.ElementTree as ET,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 linked=json.loads((ROOT/'reports/jade/stage4-wwise-event-links.json').read_text());result=[]
 for bank in linked['banks']:
  name=Path(bank['bank']).stem;dump=ROOT/'reports/jade'/('stage4-wwise-full-'+name)
  run=subprocess.run([__import__('sys').executable,str(ROOT/'tools/audio/wwiser/wwiser-master/wwiser.py'),'-d','xml','-dn',str(dump),str(ROOT/'assets'/bank['bank'])],capture_output=True,text=True,check=True)
  xml=Path(str(dump)+'.xml');tree=ET.fromstring('<banks>'+xml.read_text(encoding='utf-8')+'</banks>');nodes={}
  errors=list(tree.iter('error'));assert not errors,errors
  for chunk in tree.findall('.//object[@name="HircChunk"]'):
   for o in chunk.findall('./list/object'):
    ids=o.findall('./field[@type="sid"]')
    if not ids:continue
    identity=int(ids[0].get('value'));children=[int(f.get('value')) for f in o.findall('.//object[@name="Children"]/field[@name="ulChildID"]')];sources=sorted(set(int(f.get('value')) for f in o.findall('.//field[@name="sourceID"]')))
    nodes[identity]={'id':identity,'class':o.get('name'),'children':children,'source_ids':sources}
  def walk(identity,path):
   if identity in path:return [{'path':path+[identity],'status':'cycle'}]
   n=nodes.get(identity)
   if n is None:return [{'path':path+[identity],'status':'missing'}]
   out=[]
   if n['source_ids']:out.append({'path':path+[identity],'status':'media_candidates','source_ids':n['source_ids']})
   for child in n['children']:out.extend(walk(child,path+[identity]))
   if not out:out.append({'path':path+[identity],'status':'no_child_or_source'})
   return out
  routes=[{'action_id':a['id'],'target_id':a['target_id'],'routes':walk(a['target_id'],[])} for a in bank['actions'] if a['action_type']==1027 and a['target_type_in_bank']!=2]
  result.append({'bank':bank['bank'],'nodes':list(nodes.values()),'container_play_routes':routes,'parser_log':run.stdout,'xml_sha256':hashlib.sha256(xml.read_bytes()).hexdigest()})
 report={'parser':'wwiser v20260808','banks':result,'limits':'Children graph/media candidates only, NOT actual selected playback. Switch/state/RTPC/playlist/time/transition rules remain in XML but are not executed. Music-track source lists include all candidate media.'}
 (ROOT/'reports/jade/stage4-wwise-container-routes.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 from collections import Counter
 print(json.dumps({'container_actions':sum(len(b['container_play_routes']) for b in result),'route_status':dict(Counter(r['status'] for b in result for a in b['container_play_routes'] for r in a['routes']))}))
if __name__=='__main__':main()
