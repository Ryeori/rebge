"""Recover immutable float constants referenced by the tracking writer."""
import json
import re
import struct
from project_paths import PROJECT_ROOT,report_path


def main():
    raw=PROJECT_ROOT/'reports/ghidra/raw'
    block=json.loads((raw/'stage43-tracking-constant-block.json').read_text())['result']['structuredContent']
    code=json.loads((raw/'stage43-actor-tracking-writer.json').read_text())['result']['structuredContent']['decompiled_code']
    start=int(block['address'],16)
    data=bytes.fromhex(block['hex_data'])
    constants,excluded=[],[]
    for name in sorted(set(re.findall(r'DAT_(14173[0-9a-f]+)',code))):
        address=int(name,16);offset=address-start
        if 0<=offset<=len(data)-4:
            chunk=data[offset:offset+4]
            constants.append({'address':name,'hex':chunk.hex(),'f32':struct.unpack('<f',chunk)[0]})
        else:excluded.append(name)
    result={'constants':constants,'outside_block':excluded,
            'limits':'Numeric values only; parameter meanings and dynamic overrides not inferred.'}
    report_path('stage43-tracking-constants.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))


if __name__=='__main__':main()
