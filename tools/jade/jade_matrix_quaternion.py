"""Float32 branch arithmetic from140aecd40 and14009bae0.

Reject degenerate/nonfinite inputs rather than inventing native exceptional math.
Matrix flags, scale removal and orthogonalization are not performed by extractor.
"""
import math
from jade_animation_transition import f32


def normalize_quaternion(q):
    if len(q)!=4 or not all(math.isfinite(v) for v in q):
        raise ValueError('Finite xyzw quaternion required')
    x,y,z,w=map(f32,q)
    squared=f32(f32(f32(f32(y*y)+f32(x*x))+f32(z*z))+f32(w*w))
    if squared<=0 or not math.isfinite(squared):
        raise ValueError('Degenerate quaternion norm')
    inverse=f32(1/f32(math.sqrt(squared)))
    return [f32(v*inverse) for v in (x,y,z,w)]


def matrix_quaternion(matrix):
    if len(matrix)<16 or not all(math.isfinite(v) for v in matrix[:16]):
        raise ValueError('Finite sixteen-element matrix required')
    m=list(map(f32,matrix[:16]))
    x,y,z=m[0],m[5],m[10]
    trace=f32(f32(x+y)+z)
    mul=lambda a,b:f32(a*b)
    add=lambda a,b:f32(a+b)
    sub=lambda a,b:f32(a-b)
    if trace>0:
        branch=3
        radicand=add(trace,1)
    elif x<y:
        branch=2 if y<z else 1
        radicand=add(sub(sub(1,x),y),z) if branch==2 else sub(add(sub(1,x),y),z)
    else:
        branch=0 if z<=x else 2
        radicand=sub(sub(add(x,1),y),z) if branch==0 else add(sub(sub(1,x),y),z)
    if radicand<=0:
        raise ValueError('Degenerate matrix quaternion branch')
    root=f32(math.sqrt(radicand))
    factor=f32(0.5/root)
    if branch==3:
        q=[mul(sub(m[6],m[9]),factor),mul(sub(m[8],m[2]),factor),
           mul(sub(m[1],m[4]),factor),mul(root,0.5)]
    elif branch==0:
        q=[mul(root,0.5),mul(add(m[4],m[1]),factor),
           mul(add(m[8],m[2]),factor),mul(sub(m[6],m[9]),factor)]
    elif branch==1:
        q=[mul(add(m[4],m[1]),factor),mul(root,0.5),
           mul(add(m[9],m[6]),factor),mul(sub(m[8],m[2]),factor)]
    else:
        q=[mul(add(m[8],m[2]),factor),mul(add(m[9],m[6]),factor),
           mul(root,0.5),mul(sub(m[1],m[4]),factor)]
    return normalize_quaternion(q)
