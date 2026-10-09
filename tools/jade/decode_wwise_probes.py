import json,subprocess,wave,hashlib,re
from pathlib import Path
root=Path(__file__).resolve().parents[2]; manifest=json.loads((root/'reports/jade/stage4-wwise-audio-source-export.json').read_text()); chosen={}
for r in manifest['resources']:
 if 'format' not in r: continue
 f=r['format']; k=(f['sample_rate'],f['channels'])
 if k not in chosen or r['size']<chosen[k]['size']: chosen[k]=r
exe=root/'tools/audio/vgmstream/r2117/vgmstream-cli.exe'; rows=[]
for k,r in sorted(chosen.items()):
 src=root/'assets'/r['path']; out=root/'assets/audio/decoded-probes'/r['archive'].removesuffix('.pak')/(src.stem+'.wav'); out.parent.mkdir(parents=True,exist_ok=True)
 run=subprocess.run([str(exe),'-i','-o',str(out),str(src)],capture_output=True,text=True,check=True)
 with wave.open(str(out),'rb') as w:
  assert (w.getframerate(),w.getnchannels())==k
  n=w.getnframes(); width=w.getsampwidth(); pcm=w.readframes(n); assert len(pcm)==n*width*k[1]
 match=re.search(r'stream total samples: (\d+)',run.stdout); assert match and int(match[1])==n
 rows.append({'source':r['path'],'source_sha256':r['sha256'],'output':str(out.relative_to(root/'assets')),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'sample_rate':k[0],'channels':k[1],'samples':n,'sample_width_bytes':width,'decoder_metadata':run.stdout})
p=root/'reports/jade/stage4-wwise-decoded-probes.json'; p.write_text(json.dumps({'decoder':'vgmstream r2117 win64','options':['-i'],'resources':rows,'limits':'Representative PCM probes only, not full audio export. No event mapping or listening validation.'},indent=2),encoding='utf-8');print(json.dumps({'converted':len(rows),'sample_counts':'match decoder','formats':'match source','output_bytes':sum((root/'assets'/r['output']).stat().st_size for r in rows)}))
