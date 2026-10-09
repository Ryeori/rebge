"""Read the native GAO actor tail through confirmed flag branches; retain raw roundtrip."""
from project_paths import PROJECT_ROOT, report_path
import json,struct,hashlib
from bpak_reader import entries,decode
from jade_scene_probe import PATH
from jade_mesh import Cursor
from jade_components import parse_component4, parse_component20

def parse_tail(data, offset, flags, collision_offset):
    if flags & ((1<<21)|(1<<24)):
        raise NotImplementedError('Matrix/child array branches precede actor tail')
    c=Cursor(data);c.pos=offset;result={'flags':f'{flags:08X}'}
    if flags&(1<<13):
        result['action_block_offset']=c.pos
        result['action_words']=c.read('4I')
        c.skip(16);c.skip(4)
        result['action_initial_index']=c.read('H');c.skip(2)
        result['action_bytes']=c.read('2B');result['action_flags']=c.read('H')
    references={}
    for bit,label in ((5,'hierarchy'),(25,'extra25'),(27,'brain'),(18,'extra18'),(4,'extra_object')):
        if flags&(1<<bit): references[label]=f'{c.read("I"):08X}'
    result['references']=references
    if flags&(1<<6):
        result['dynamics_offset']=c.pos;c.skip(4)
        result['dynamics_words']=c.read('5I')
        result['dynamics_vector14']=c.read('3f');result['dynamics_vector20']=c.read('3f')
        result['dynamics_tail_words']=c.read('11I')
    if flags&0x600:
        if c.pos!=collision_offset:
            if not result.get('action_words',[0,0])[1] or c.pos>collision_offset:
                raise ValueError('Unexpected component boundary')
            if struct.unpack_from('<I',data,collision_offset-4)[0]!=0xffffffff:
                raise ValueError('Missing recursive component terminator')
            opaque=data[c.pos:collision_offset]
            result['opaque_component_chain']={'offset':c.pos,'size':len(opaque),'first_type':struct.unpack_from('<I',opaque)[0],'sha256':hashlib.sha256(opaque).hexdigest(),'limits':'Length from independently validated collision tail; component body not decoded'}
            if struct.unpack_from('<I',opaque)[0]==4:
                component=parse_component4(data,c.pos)
                result['component4']={k:v for k,v in component.items() if k not in ('primary','secondary')}
                result['component4']['primary_group_counts']=[g['count'] for g in component['primary']]
                result['component4']['secondary_group_counts']=[g['count'] for g in component['secondary']]
                result['component4']['next_type']=struct.unpack_from('<I',data,component['end_offset'])[0]
                result['component4']['limits']='Native update confirms additive vertex deltas; timeline driver and object identity unresolved'
                if result['component4']['next_type'] == 20:
                    tail_component = parse_component20(data, component['end_offset'])
                    result['component20'] = tail_component
                    if tail_component['end_offset'] != collision_offset-4:
                        raise ValueError(f'Component 20 boundary {tail_component}, expected {collision_offset-4}')
            c.skip(len(opaque))
        result['collision_offset']=c.pos;references['collision']=f'{c.read("I"):08X}'
    if flags&(1<<8):references['shape_list']=f'{c.read("I"):08X}'
    extra=c.read('I');c.skip(extra)
    result['remaining']=len(data)-c.pos
    if result['remaining']!=40:raise ValueError(f'Tail boundary mismatch: length={len(data)} cursor={c.pos} extra={extra} fields={result}')
    if c.rebuild()!=data:raise ValueError('Roundtrip mismatch')
    result['roundtrip']=True
    return result

def main():
    index={e['name']:e for e in entries(PATH)}
    objects=json.load(open(report_path('hangar-object-probe.json')))
    callbacks=json.load(open(report_path('stage4-native-callbacks.json')))['callbacks']
    collision_offsets={r['object']:r['reference_offset'] for r in json.load(open(report_path('hangar-spatial-validation.json')))['collision_objects']}
    report=[]
    with PATH.open('rb') as f:
        def load(k):return decode(f,index[k])
        for obj in objects:
            if obj['key'] not in ('D9005D4A','3D0030FF'):continue
            data=load(obj['key']);result=parse_tail(data,obj['after_visual'],int(obj['flags'],16),collision_offsets[obj['key']]);result['object']=obj['key']
            result['reference_metadata']=[]
            for role,key in result['references'].items():
                if key not in index:continue
                payload=load(key)
                found=[]
                for row in callbacks:
                    needle=struct.pack('<I',int(row['key'],16))
                    offset=payload.find(needle)
                    if offset>=0 and ('Sally' in row['name'] or 'Jade' in row['name']):found.append({'name':row['name'],'offset':offset})
                result['reference_metadata'].append({'role':role,'key':key,'size':len(payload),'callback_key_occurrences':found,'first_words':[f'{v:08X}' for v in struct.unpack_from(f'<{min(8,len(payload)//4)}I',payload)]})
            report.append(result)
    open(report_path('stage4-actor-fields.json'),'w').write(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
