"""Native type-1 mesh reader, following the confirmed Ghidra resource cursor."""
from project_paths import PROJECT_ROOT, report_path
import struct, math
class Cursor:
    def __init__(self,data):self.data=data;self.pos=0;self.records=[]
    def read(self,fmt):
        n=struct.calcsize('<'+fmt)
        if self.pos+n>len(self.data):raise ValueError(f'Truncated record at {self.pos}')
        value=struct.unpack_from('<'+fmt,self.data,self.pos);self.records.append((self.pos,fmt,value));self.pos+=n
        return value[0] if len(value)==1 else value
    def skip(self,n):
        if n<0 or n>len(self.data)-self.pos:raise ValueError(f'Invalid skip {n} at {self.pos}')
        self.pos+=n
    def rebuild(self):
        result=bytearray(self.data)
        for offset,fmt,value in self.records:struct.pack_into('<'+fmt,result,offset,*value)
        return bytes(result)
def parse_mesh(data):
    c=Cursor(data)
    if c.read('I')!=1:raise ValueError('Not native mesh type 1')
    c.skip(c.read('I'))
    nv,nc,nu,ns=c.read('4I');c.skip(4)
    extra,mask=c.read('2I')
    if max(nv,nc,nu,ns)>1000000:raise ValueError('Unreasonable mesh counts')
    extension = None
    if mask&0xc0de2002==0xc0de2002:
        version,count=c.read('2H'); records=[]
        for _ in range(count):
            bone,n=c.read('2H'); matrix=list(c.read('16f')); flags=c.read('I')
            words=[c.read('I') for _ in range(n)]
            records.append({'index_u16':bone,'matrix':matrix,'matrix_flags':flags,'words_u32':words})
        extension={'version':version,'records':records,'limits':'Native1542eec90 source order; words interpreted by140a41f90 as shared float32 weight/low16 vertex index; runtime bind composition still explicit.'}
    if mask&1:
        groups=c.read('I')
        for _ in range(groups):
            n=c.read('I');c.skip(24)
            for _ in range(n):
                bone,count=c.read('2H');c.skip(count*2)
    positions=[c.read('3f') for _ in range(nv)]; legacy_normals=[c.read('3f') for _ in range(nv)]
    if not all(math.isfinite(v) for p in positions for v in p):raise ValueError('Nonfinite vertex')
    if extra:raise NotImplementedError('Auxiliary vertex block')
    colors=[c.read('I') for _ in range(min(nv,nc))] if nc else []
    uvs=[c.read('2f') for _ in range(nu)]
    headers=[]
    for _ in range(ns):
        ntri,unknown,aux,strip=c.read('4I');c.skip(24)
        if ntri>1000000 or strip>10000000:raise ValueError('Unreasonable submesh counts')
        headers.append((ntri,unknown,aux,strip))
    submeshes=[]
    for ntri,unknown,aux,strip in headers:
        triangles=[c.read('6H2I') for _ in range(ntri)]
        if any(max(t[:3])>=nv for t in triangles):raise ValueError('Vertex index out of range')
        if nu and any(max(t[3:6])>=nu for t in triangles):raise ValueError('UV index out of range')
        if aux:c.skip(12)
        if strip:c.skip(strip*2)
        submeshes.append({'triangles':triangles,'unknown':unknown,'aux':aux,'strip':strip})
    if c.rebuild()!=data:raise ValueError('Mesh read/write round trip failed')
    return {'extended_header':extension,'legacy_normals':legacy_normals,'positions':positions,'colors':colors,'uvs':uvs,'submeshes':submeshes,
            'trailing_offset':c.pos,'trailing_size':len(data)-c.pos,'mask':mask}
