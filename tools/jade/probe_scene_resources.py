"""Bounded resource census; writes metadata only, never extracted payloads."""
from project_paths import PROJECT_ROOT, report_path
import collections, hashlib, json, pathlib, struct
from bpak_reader import entries, decode

def main():
    path=pathlib.Path(r'E:\SteamLibrary\steamapps\common\Beyond Good and Evil - 20th Anniversary Edition\Data\Paks\Resources.pak')
    counts=collections.Counter(); samples={}; errors=[]; skipped=0
    with path.open('rb') as f:
        for e in entries(path):
            if e['unpacked']>8*1024*1024:
                skipped+=1; continue
            try: data=decode(f,e)
            except Exception as exc:
                errors.append({'key':e['name'],'error':str(exc)}); continue
            prefix=data[:4]
            tag=prefix.decode('ascii') if len(prefix)==4 and all(32<=x<127 for x in prefix) else prefix.hex()
            counts[tag]+=1
            if tag.startswith('.') or tag in ('DDS ','mtx ','PNG ','.gao'):
                bucket=samples.setdefault(tag,[])
                if len(bucket)<30:
                    bucket.append(dict(e,sha256=hashlib.sha256(data).hexdigest(),prefix_hex=data[:96].hex()))
    report={'counts':dict(counts.most_common()),'samples':samples,'errors':errors,'skipped_over_8MiB':skipped}
    pathlib.Path(report_path('scene-resource-census.json')).write_text(json.dumps(report,indent=2))
    print(json.dumps({'top':counts.most_common(40),'sample_tags':list(samples),'errors':len(errors),'skipped':skipped}))
if __name__=='__main__': main()
