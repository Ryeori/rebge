"""Source role tags from native153629c80, used by1409c18e0."""
import json
from bpak_reader import entries,decode
from jade_scene_probe import PATH
from project_paths import report_path


def decode_roles(data):
    if not data:raise ValueError('Missing count')
    count=min(data[0],64)
    if len(data)<1+count*3:raise ValueError('Truncated role records')
    roles=[255]*64
    auxiliary=[255]*64
    for index in range(count):
        slot,role,other=data[1+index*3:4+index*3]
        if slot>=64:raise ValueError('Slot outside ordinary64-entry role table')
        roles[slot]=role;auxiliary[slot]=other
    return {'roles':roles,'auxiliary':auxiliary,'opaque_tail_hex':data[1+count*3:].hex()}


def main():
    index={entry['name']:entry for entry in entries(PATH)}
    with PATH.open('rb') as archive:
        raw=decode(archive,index['A9001F3E'])
    result={'source_key':'A9001F3E','source_size':len(raw),**decode_roles(raw)}
    result['tracking_role_candidates']={str(role):[slot for slot,tag in enumerate(result['roles']) if tag==role]
                                        for role in (0,1,12)}
    result['limits']='Source role tags only; current native table identity not yet compared.'
    report_path('stage43-sally-tracking-roles.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))


if __name__=='__main__':main()
