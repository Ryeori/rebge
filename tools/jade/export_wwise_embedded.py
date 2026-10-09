import json,subprocess,wave,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 banks=json.loads((ROOT/'reports/jade/stage4-wwise-bank-structure.json').read_text())['banks'];rows=[];probes=[]
 for b in banks:
  full=[m for m in b['media'] if m['status']=='complete'];data=(ROOT/'assets'/b['path']).read_bytes();exported=[]
  for m in full:
   out=ROOT/'assets/audio/wwise-source'/Path(b['path']).parts[2]/'embedded'/Path(b['path']).stem/(str(m['media_id'])+'.wem');out.parent.mkdir(parents=True,exist_ok=True);raw=data[m['offset']:m['offset']+m['size']];out.write_bytes(raw)
   row={'bank':b['path'],'media_id':m['media_id'],'path':str(out.relative_to(ROOT/'assets')),'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()};assert row['sha256']==m['sha256'];rows.append(row);exported.append(row)
  if exported:
   r=min(exported,key=lambda r:r['size']);src=ROOT/'assets'/r['path'];wav=ROOT/'assets/audio/decoded-probes/embedded'/Path(b['path']).stem/(src.stem+'.wav');wav.parent.mkdir(parents=True,exist_ok=True)
   run=subprocess.run([str(ROOT/'tools/audio/vgmstream/r2117/vgmstream-cli.exe'),'-i','-o',str(wav),str(src)],capture_output=True,text=True,check=True)
   with wave.open(str(wav),'rb') as w:
    n=w.getnframes();channels=w.getnchannels();rate=w.getframerate();assert len(w.readframes(n))==n*channels*w.getsampwidth()
   assert n==int(re.search(r'stream total samples: (\d+)',run.stdout)[1])
   probes.append({'source':r['path'],'output':str(wav.relative_to(ROOT/'assets')),'samples':n,'channels':channels,'sample_rate':rate,'metadata':run.stdout,'sha256':hashlib.sha256(wav.read_bytes()).hexdigest()})
 (ROOT/'reports/jade/stage4-wwise-embedded-export.json').write_text(json.dumps({'resources':rows,'decoded_probes':probes,'limits':'Complete embedded RIFF only. Prefetch remains indexed in banks; use full streamed WEM for decoding. Event roles unclassified.'},indent=2),encoding='utf-8');print(json.dumps({'complete_files':len(rows),'decoded_probes':len(probes),'bytes':sum(r['size'] for r in rows)}))
if __name__=='__main__':main()
