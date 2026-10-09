"""Lossless TXI/TXS reader and local localization exporter inside the private project."""
from project_paths import PROJECT_ROOT, report_path
import argparse,collections,hashlib,json,pathlib,re,struct,sys
from bpak_reader import entries,decode
LOCALES={'en':('Text-en_US.pak',1),'ru':('Text-ru.pak',11)}
UNICODE=re.compile(r'\\[Uu]\+(\d+)\\')

def display_text(raw):
    text=raw.decode('cp1252',errors='replace')
    def repl(m):
        n=int(m.group(1))
        return chr(n) if n<=0x10ffff and not 0xd800<=n<=0xdfff else m.group(0)
    return UNICODE.sub(repl,text)

def parse_pair(txi,txs):
    if len(txi)%68:raise ValueError('TXI length must be divisible by 68')
    records=[]
    for pos in range(0,len(txi),68):
        offset=struct.unpack_from('<I',txi,pos)[0];field=txi[pos+4:pos+68]
        if offset>=len(txs):raise ValueError(f'TXS offset outside buffer: {offset}')
        end=txs.find(b'\0',offset)
        if end<0:raise ValueError(f'Unterminated TXS string at {offset}')
        name_end=field.find(b'\0')
        name=field if name_end<0 else field[:name_end]
        raw=txs[offset:end]
        records.append({'index':pos//68,'offset':offset,'name':name.decode('cp1252',errors='replace'),'name_field_hex':field.hex(),'text_bytes_hex':raw.hex(),'text_source':raw.decode('cp1252',errors='replace'),'text_display':display_text(raw)})
    return records

def encode_txi(records):
    out=bytearray()
    for r in records:
        field=bytes.fromhex(r['name_field_hex'])
        if len(field)!=64:raise ValueError('name field must contain exactly 64 bytes')
        out+=struct.pack('<I',r['offset'])+field
    return bytes(out)

def load_tables(base,mapping):
    es={e['name']:e for e in entries(base/'Resources.pak')}
    with (base/'Resources.pak').open('rb') as f:
        for g in mapping:
            data=decode(f,es[g['resource']])
            if len(data)!=208:raise ValueError('Unexpected locale-table size')
            rows=[]
            for pos in range(0,208,16):
                first,m1,second,m2=struct.unpack_from('<I4sI4s',data,pos)
                if m1!=b'.txi' or m2!=b'.txs':raise ValueError('Invalid locale-table markers')
                rows.append((f'{first:08X}',f'{second:08X}'))
            yield g['resource'],rows

def export(game,mapping_path,output,summary_path):
    workspace=PROJECT_ROOT;output=output.resolve();game=game.resolve()
    if not output.is_relative_to(workspace) or output==workspace or output.is_relative_to(game):raise ValueError('Output must be a project subdirectory, outside the game installation')
    output.mkdir(parents=True,exist_ok=True)
    base=game/'Data'/'Paks';mapping=json.loads(mapping_path.read_text(encoding='utf-8'))['candidates'];tables=list(load_tables(base,mapping))
    reports=[];by_group={};roundtrips=0;raw_digests=[]
    for loc,(file,langidx) in LOCALES.items():
        es={e['name']:e for e in entries(base/file)};stats=collections.Counter();tokens=collections.Counter();by_group[loc]={}
        with (base/file).open('rb') as f:
            for group,rows in tables:
                ki,ks=rows[langidx];txi=decode(f,es[ki]);txs=decode(f,es[ks]);records=parse_pair(txi,txs)
                if encode_txi(records)!=txi:raise ValueError('TXI round trip mismatch')
                roundtrips+=1
                # Preserve the complete TXS buffer, including unreachable bytes, terminators and padding.
                payload={'schema':1,'group':group,'locale':loc,'txi_key':ki,'txs_key':ks,'txi_sha256':hashlib.sha256(txi).hexdigest(),'txs_sha256':hashlib.sha256(txs).hexdigest(),'txs_buffer_hex':txs.hex(),'records':records}
                target=output/loc/(group+'.json');target.parent.mkdir(exist_ok=True)
                target.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
                reread=json.loads(target.read_text(encoding='utf-8'))
                if encode_txi(reread['records'])!=txi or bytes.fromhex(reread['txs_buffer_hex'])!=txs:raise ValueError('JSON lossless round trip mismatch')
                raw_digests.append({'group':group,'locale':loc,'txi_sha256':payload['txi_sha256'],'txs_sha256':payload['txs_sha256']})
                stats['groups']+=1;stats['records']+=len(records);stats['unicode_tokens']+=sum(len(UNICODE.findall(r['text_source'])) for r in records)
                stats['unnamed_records']+=sum(not r['name'] for r in records)
                for r in records:
                    for token in re.findall(r'\\([^\\\r\n]*)\\',r['text_source']):
                        normalized=re.sub(r'\d+','#',token)
                        if len(normalized)<30:tokens[normalized]+=1
                by_group[loc][group]=records
        reports.append({'locale':loc,'statistics':dict(stats),'control_patterns':dict(tokens.most_common(30))})
    mismatches=[];matched=0
    for group,_ in tables:
        a=collections.Counter(r['name'] for r in by_group['en'][group]);b=collections.Counter(r['name'] for r in by_group['ru'][group]);matched+=sum((a&b).values())
        if a!=b:mismatches.append({'group':group,'en_records':sum(a.values()),'ru_records':sum(b.values()),'en_only_names':list((a-b).elements()),'ru_only_names':list((b-a).elements())})
    result={'schema':1,'output_directory':str(output),'group_count':len(tables),'txi_roundtrips':roundtrips,'json_lossless_pair_roundtrips':roundtrips,'matched_named_occurrences':matched,'locales':reports,'name_mismatches':mismatches,'hashes':raw_digests,'limitations':['Unicode conversion is a display interpretation; all source bytes and other control codes are preserved.','No runtime game/UI verification or resource repacking.']}
    summary_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='hashes'},ensure_ascii=False,indent=2))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--game',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path,required=True);ap.add_argument('--mapping',type=pathlib.Path,default=pathlib.Path(report_path('jade-language-key-mapping.json')));ap.add_argument('--summary',type=pathlib.Path,default=pathlib.Path(report_path('localization-validation.json')));args=ap.parse_args();export(args.game,args.mapping,args.output,args.summary)
if __name__=='__main__':main()
