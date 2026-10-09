"""Export bounded modifier parameters from the saved two-resource probe."""
import json
import struct
from jade_modifier24 import decode_source_record,encode_source_record
from project_paths import ASSET_ROOT,report_path


def main():
    sources=json.loads(report_path('stage43-slot28-source-resources.json').read_text())
    out=ASSET_ROOT/'modifiers/sally';out.mkdir(parents=True,exist_ok=True)
    for item in sources:
        raw=bytes.fromhex(item['unparsed_tail_hex']);record=decode_source_record(raw)
        if encode_source_record(record)!=raw[:record['consumed_bytes']]:
            raise ValueError('Modifier source roundtrip failed')
        offset=record['consumed_bytes'];name_length=struct.unpack_from('<I',raw,offset)[0]
        if not 0<name_length<=256 or offset+4+name_length>len(raw):raise ValueError('Invalid source name length')
        name=raw[offset+4:offset+4+name_length].rstrip(b'\0').decode('ascii')
        record.update(schema='jade-modifier24-source-v1',gao_key=item['key'],source_sha256=item['sha256'],
            source_record_offset=item['unparsed_tail_offset'],source_name=name,
            evidence=['1409afac0','153464450','1409b05fe','153ca5d50','1409dcba0'],
            limitations=['Parameter export and roundtrip only; stateful motion and callback ordering not yet verified.'])
        slot=28 if item['key']=='620007AA' else 27
        path=out/f"slot{slot}-{item['key']}.json"
        path.write_text(json.dumps(record,indent=2));print(path,hex(record['mode_flags']),name)


if __name__=='__main__':main()
