"""Native140a41f90 skin word decoding and float32 accumulation.
Matrices must be supplied after native bind/runtime composition; no guessed pose.
"""
import math,struct
from jade_pose import affine_product

def f32(value):return struct.unpack('<f',struct.pack('<f',value))[0]
def decode_skin_word(word):
 weight=struct.unpack('<f',struct.pack('<I',word))[0]
 if not math.isfinite(weight):raise ValueError('Nonfinite skin weight')
 return {'vertex':word&0xffff,'weight':weight,'source_word':word}

def compose_skin_matrix(bind,bind_flags,bone,bone_flags,mirror_bind_x=False):
 """140a43a00->140ae9c00 no-scale branch: bone*bind, flag-selected fields.

 Source flags are authoritative even when unused matrix storage is zero.
 Scale requires native decomposition/rounding and is explicitly excluded.
 """
 def effective(matrix,flags):
  if len(matrix)!=16:raise ValueError('Matrix requires 16 floats')
  if flags&8:raise NotImplementedError('Scaled skin matrix composition')
  out=[0.0]*16;out[0]=out[5]=out[10]=out[15]=1.0
  if flags&4:
   for c in range(3):
    for r in range(3):out[c*4+r]=matrix[c*4+r]
  if flags&2:out[12:15]=matrix[12:15]
  return out
 bind=list(bind)
 if mirror_bind_x:
  for i in (0,4,8,12):bind[i]=-bind[i]
 matrix=affine_product(effective(bind,bind_flags),effective(bone,bone_flags))
 flags=(bind_flags|bone_flags)&4
 if any(v!=0.0 for v in matrix[12:15]):flags|=2
 return {'matrix':matrix,'flags':flags}
def deform_vertices(positions,records,matrices):
 out=[[0.0,0.0,0.0] for _ in positions]
 # Native traverses extension pointer array in reverse, cancelling loader reversal.
 for record in records:
  index=record['index_u16']
  if index not in matrices:raise ValueError('Missing runtime skin matrix')
  m=matrices[index]['matrix'];flags=matrices[index]['flags'];mode=flags&14
  if len(m)!=16:raise ValueError('Matrix requires 16 floats')
  for word in record['words_u32']:
   influence=decode_skin_word(word);v=influence['vertex'];w=influence['weight']
   if v>=len(positions):raise ValueError('Skin vertex out of bounds')
   p=positions[v];q=[]
   for axis in range(3):
    if mode&4:
     scaled=[f32(p[j]*m[j*4+3]) if mode&8 else p[j] for j in range(3)]
     terms=[f32(scaled[j]*m[j*4+axis]) for j in range(3)]
     # Native general branch adds y + x + z; scalar instruction rounding.
     value=f32(f32(terms[1]+terms[0])+terms[2])
    elif mode&8:value=f32(p[axis]*m[axis*4+3])
    else:value=p[axis]
    if mode&2:value=f32(value+m[12+axis])
    q.append(f32(f32(value*w)+out[v][axis]))
   out[v]=q
 return out
