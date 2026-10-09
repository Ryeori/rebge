"""Spatial-grid fields and collision references located from the confirmed GAO tail."""
from project_paths import PROJECT_ROOT, report_path
import collections,hashlib,json,struct
from bpak_reader import entries,decode
from jade_scene_probe import PATH
from jade_mesh import Cursor
def main():
    index={e['name']:e for e in entries(PATH)};report={'grids':[],'collision_objects':[]}
    with PATH.open('rb') as f:
        def load(key):return decode(f,index[key])
        for key in ('D9006AA6','D9005818'):
            data=load(key);nx,ny=struct.unpack_from('<2h',data,40)
            if len(data)!=60+nx*ny*4:raise ValueError('Grid cell size mismatch')
            cells=struct.unpack_from(f'<{nx*ny}I',data,60);root=struct.unpack_from('<I',data,8)[0]
            report['grids'].append({'key':key,'dimensions':[nx,ny],'list_key':f'{root:08X}','list_present':f'{root:08X}' in index,
                'cell_offsets_min':min(cells),'cell_offsets_max':max(cells),'sha256':hashlib.sha256(data).hexdigest()})
        objects=json.load(open(report_path('hangar-object-probe.json')))
        for obj in objects:
            flags=int(obj['flags'],16)
            if not flags&0x600:continue
            data=load(obj['key']);version=struct.unpack_from('<I',data,4)[0]
            if version!=2:raise ValueError('Unsupported GAO tail version')
            # Version-2 RGBA + word (20), native legacy fields (20), skipped payload length (4).
            end=len(data)-40
            candidates=[]
            for p in range(obj['after_visual'],end-3):
                n=struct.unpack_from('<I',data,p)[0]
                if p+4+n!=end:continue
                refpos=p-4-(4 if flags&0x100 else 0)
                ref=f'{struct.unpack_from("<I",data,refpos)[0]:08X}'
                if ref in index:
                    payload=load(ref)
                    if len(payload)>=4 and f'{struct.unpack_from("<I",payload)[0]:08X}' in index:candidates.append(p)
            if len(candidates)!=1:raise ValueError(f'Ambiguous GAO tail: {candidates}')
            skip_offset=candidates[0]
            pos=skip_offset-4-(4 if flags&0x100 else 0)
            collision_key=f'{struct.unpack_from("<I",data,pos)[0]:08X}'
            instance=load(collision_key);shape_key=f'{struct.unpack_from("<I",instance)[0]:08X}'
            c=Cursor(load(shape_key));count,unknown=c.read('2B');c.skip(2);c.skip(16);shapes=[]
            for _ in range(count):
                header=c.read('4B');extra=c.read('I');c.skip(extra);c.skip(1);kind=header[1]
                fields={1:6,2:4,3:5}.get(kind)
                if fields is None:raise ValueError(f'Unsupported collision shape {kind}')
                values=c.read(f'{fields}f');shapes.append({'kind':kind,'fields':values})
            if c.pos!=len(c.data) or c.rebuild()!=c.data:raise ValueError('Collision shape round trip failed')
            report['collision_objects'].append({'object':obj['key'],'instance_key':collision_key,'shape_key':shape_key,
                'shape_count':count,'shapes':shapes,'roundtrip':True,'reference_offset':pos,'trailing_skipped_bytes':end-skip_offset-4,
                'limits':'Shape kind byte confirmed; physical semantics and active flags require stage 4 oracle.'})
    json.dump(report,open(report_path('hangar-spatial-validation.json'),'w'),indent=2);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
