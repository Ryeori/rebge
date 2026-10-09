"""Lossless component-4 structural reader from native virtual reader 1409d49d0.

Component-4 update 1409d3670 confirms additive vertex displacements.
The timeline driver and character identity remain unresolved.
"""
from project_paths import PROJECT_ROOT, report_path
from jade_mesh import Cursor
import struct

def parse_component4(data, offset):
    c=Cursor(data);c.pos=offset
    kind=c.read('I');instance=c.read('I')
    if kind!=4:raise ValueError('Requires component 4')
    c.skip(4)
    field0,field20,primary_count,secondary_count=c.read('4I')
    if max(primary_count,secondary_count)>65536:raise ValueError('Unreasonable component count')
    primary=[];secondary=[]
    for _ in range(primary_count):
        count=c.read('I');c.skip(64)
        if count>1000000:raise ValueError('Unreasonable primary count')
        indices=[c.read('I') for _ in range(count)]
        words=[c.read('3I') for _ in range(count)]
        primary.append({'count':count,'indices':indices,'words':words})
    for _ in range(secondary_count):
        count,word1,word2=c.read('3I');c.skip(64)
        if count>1000000:raise ValueError('Unreasonable secondary count')
        indices=[c.read('I') for _ in range(count)]
        secondary.append({'count':count,'word1':word1,'word2':word2,'indices':indices})
    if c.rebuild()!=data:raise ValueError('Component roundtrip failed')
    return {'offset':offset,'end_offset':c.pos,'instance':instance,'field0':field0,'field20':field20,
            'primary':primary,'secondary':secondary,'roundtrip':True}

def parse_component20(data, offset):
    """Reader 1409d03b0 -> 15382da90; source fields remain provisional."""
    c = Cursor(data); c.pos = offset
    if c.read('I') != 20:
        raise ValueError('Requires component 20')
    instance = c.read('I')
    words = c.read('4I')
    scalars = c.read('4f')
    # DAT_14173c8ec = c5 20 80 3f, verified with Ghidra memory/read.
    sentinel = struct.unpack('<f', bytes.fromhex('c520803f'))[0]
    # Matching sentinel consumes stored vectors; otherwise runtime zeros them.
    vectors = [c.read('3f'), c.read('3f')] if scalars[3] == sentinel else []
    final_scalar = c.read('f')
    if c.rebuild() != data:
        raise ValueError('Component 20 roundtrip failed')
    return {'offset': offset, 'end_offset': c.pos, 'instance': instance,
            'words': words, 'scalars': scalars, 'vectors': vectors,
            'final_scalar': final_scalar, 'roundtrip': True}
