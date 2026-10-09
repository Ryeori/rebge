"""Restricted140b482f0 consumer from explicit native segment state.

Host transcendental functions remain numerical substitutes. No matrix-valued
keys, alternate endpoints, or time remapping supported.
"""
import math
import struct
from jade_animation_transition import f32
from jade_matrix_quaternion import normalize_quaternion
from jade_animation import packed_quaternion_float32

EPSILON=struct.unpack('<f',bytes.fromhex('95bfd633'))[0]


def interpolate_channel(first,second,fraction):
    a,b=[list(map(f32,q)) for q in (first,second)]
    dot=f32(f32(f32(f32(a[1]*b[1])+f32(a[0]*b[0]))+f32(a[2]*b[2]))+f32(a[3]*b[3]))
    if dot<0:dot=-dot;b=[-v for v in b]
    dot=min(1,dot)
    if abs(f32(dot-1))<=EPSILON:return a
    angle=f32(math.acos(dot))
    inverse=f32(1/f32(math.sqrt(f32(1-f32(dot*dot)))))
    t=f32(fraction)
    left=f32(f32(math.sin(f32(f32(1-t)*angle)))*inverse)
    right=f32(f32(math.sin(f32(t*angle)))*inverse)
    return normalize_quaternion([f32(f32(x*left)+f32(y*right)) for x,y in zip(a,b)])


def rotation_at_state(track,state):
    frames=track['frames'];index=state['frame_index']
    if not 0<=index<len(frames):raise ValueError('Frame index outside source')
    frame=frames[index];following=frames[(index+1)%len(frames)]
    elapsed=state['elapsed_seconds']
    if not math.isfinite(elapsed) or elapsed<0:raise ValueError('Finite forward segment required')
    def quaternion(key):
        transform=key.get('transform',{});flags=transform.get('flags',0)
        if flags&(4|8|0x40):raise ValueError('Matrix key/time remapping/alternate endpoint unsupported')
        q=(packed_quaternion_float32(transform['packed_rotation']) if 'packed_rotation' in transform
           else transform.get('quaternion_xyzw'))
        if q is None:return None
        q=list(map(f32,q))
        if key['flags']&0x20:q[1]=-q[1];q[2]=-q[2]
        return q
    current=quaternion(frame)
    if current is None:return None
    next_value=quaternion(following)
    if frame['tick_raw']==0 or next_value is None or frame['flags']&0x800:return current
    duration=f32(frame['tick_raw']/60)
    if duration<=elapsed:return next_value
    return interpolate_channel(current,next_value,f32(elapsed/duration))
