"""Read-only BPAK payload validation. No game assets are written."""
from project_paths import PROJECT_ROOT, report_path
import argparse, collections, hashlib, io, json, pathlib, struct, sys
sys.path.insert(0,str(PROJECT_ROOT/'.dependencies'))
import lz4.block

def entries(path):
    path=pathlib.Path(path)
    with path.open('rb') as f:
        header=f.read(24)
        if len(header)!=24: raise ValueError('Truncated BPAK header')
        magic,word4,priority,flag,count,index_size=struct.unpack('<4s5I',header)
        size=f.seek(0,2)
        if magic!=b'BPAK' or index_size>size-24: raise ValueError('Invalid header')
        if count>index_size//29: raise ValueError('Impossible BPAK entry count')
        f.seek(size-index_size); table=f.read(index_size)
    pos=0
    def require(n):
        if n>len(table)-pos: raise ValueError('Truncated BPAK index')
    for i in range(count):
        require(5)
        kind=table[pos];pos+=1
        if kind==0:
            n=struct.unpack_from('<I',table,pos)[0];pos+=4
            require(n)
            name=table[pos:pos+n].decode('utf-8',errors='replace');pos+=n
        elif kind==1:
            name=f'{struct.unpack_from("<I",table,pos)[0]:08X}';pos+=4
        else: raise ValueError(f'Unknown entry kind {kind}')
        require(24)
        unpacked,packed,unknown,relative=struct.unpack_from('<IIQQ',table,pos);pos+=24
        if relative+24+(packed or unpacked)>size-index_size:raise ValueError('Payload outside data area')
        yield dict(index=i,name=name,kind=kind,unpacked=unpacked,packed=packed,unknown=unknown,offset=relative+24)
    if pos!=index_size: raise ValueError('Index size mismatch')

def decode(f,e):
    f.seek(e['offset']); raw=f.read(e['packed'] or e['unpacked'])
    if len(raw)!=(e['packed'] or e['unpacked']):raise ValueError('Truncated payload')
    data=lz4.block.decompress(raw,uncompressed_size=e['unpacked']) if e['packed'] else raw
    if len(data)!=e['unpacked']:raise ValueError('Unpacked length mismatch')
    return data

def classify(data):
    for sig,name in [(b'\x89PNG\r\n\x1a\n','PNG'),(b'DXBC','DXBC'),(b'DDS ','DDS'),(b'RIFF','RIFF'),(b'.gao','GAO'),(b'FONTDESC','FONTDESC')]:
        if data.startswith(sig):return name
    if data.startswith(b'\xef\xbb\xbf'):return 'UTF8-BOM'
    if data.startswith(b'['):return 'INI-like'
    return 'unknown'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--game',default=r'E:\SteamLibrary\steamapps\common\Beyond Good and Evil - 20th Anniversary Edition');ap.add_argument('--output',default=report_path('pak-payload-validation.json'));args=ap.parse_args()
    base=pathlib.Path(args.game)/'Data'/'Paks';reports=[]
    for archive in ['Engine.pak','Text-en_US.pak','Text-ru.pak','Resources.pak','Shaders.pak']:
        path=base/archive; report=dict(archive=archive,verified=0,compressed_verified=0,skipped=0,errors=[],types={},examples=[]);types=collections.Counter()
        with path.open('rb') as f:
            for e in entries(path):
                # Bound exploratory reads to 128 payloads per large archive and 2 MiB per entry.
                if e['unpacked']>2*1024*1024 or (archive in ('Resources.pak','Shaders.pak') and report['verified']>=128): report['skipped']+=1;continue
                try:
                    data=decode(f,e);kind=classify(data);types[kind]+=1
                    report['verified']+=1;report['compressed_verified']+=bool(e['packed'])
                    example=dict(e,type=kind,sha256=hashlib.sha256(data).hexdigest(),prefix_hex=data[:24].hex())
                    if kind=='PNG':
                        from PIL import Image
                        with Image.open(io.BytesIO(data)) as im: example['image_size']=list(im.size);im.verify()
                        with Image.open(io.BytesIO(data)) as im:im.load()
                    if len(report['examples'])<12:report['examples'].append(example)
                except Exception as exc: report['errors'].append(dict(index=e['index'],name=e['name'],error=str(exc)))
        report['types']=dict(types);reports.append(report)
        print(archive,'verified',report['verified'],'lz4',report['compressed_verified'],'types',dict(types),'errors',len(report['errors']))
    pathlib.Path(args.output).write_text(json.dumps(reports,indent=2),encoding='utf-8')
    return int(any(r['errors'] for r in reports))
if __name__=='__main__':sys.exit(main())
