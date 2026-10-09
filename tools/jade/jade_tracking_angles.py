"""Restricted pitch helper1409b4b30 for finite unit vectors.

Uses host libm acos; not a bit-exact native math-library implementation.
Degenerate horizontal projections explicitly require a separate native branch.
"""
import math
from jade_animation_transition import f32
from jade_basis_normalize import normalize_vector, cross


def yaw_difference(first, second, sign_axis):
    """1409b4d30 projected angle; explicit axis from runtime global.

    140036db0 returns cross magnitude with sign from dot(cross,axis).
    Host acos is used; no bit-exact native transcendental claim.
    """
    vectors = []
    for vector in (first, second):
        if len(vector) != 3 or not all(math.isfinite(v) for v in vector):
            raise ValueError('Expected finite XYZ')
        projected = normalize_vector([vector[0], vector[1], 0])
        if not any(projected):
            raise ValueError('Zero horizontal projection unsupported')
        vectors.append(projected)
    if len(sign_axis) != 3 or not all(math.isfinite(v) for v in sign_axis):
        raise ValueError('Expected explicit finite sign axis')
    a, b = vectors
    dot = f32(f32(f32(a[0]*b[0]) + f32(a[1]*b[1])) + f32(a[2]*b[2]))
    if dot >= 1:
        return 0.0
    angle = f32(math.pi) if dot <= -1 else f32(math.acos(dot))
    # Native sign helper normalizes the already projected vectors again.
    product = cross(normalize_vector(a), normalize_vector(b))
    axis = list(map(f32, sign_axis))
    sign = f32(f32(f32(product[1]*axis[1]) + f32(product[0]*axis[0]))
               + f32(product[2]*axis[2]))
    if sign < 0:
        angle = -angle
    pi, two_pi = f32(math.pi), f32(2*math.pi)
    if angle > pi:
        angle = f32(angle - two_pi)
    if angle < -pi:
        angle = f32(angle + two_pi)
    return angle


def pitch_difference(first,second):
    pi=f32(math.pi);two_pi=f32(2*math.pi);half_pi=f32(math.pi/2)
    def elevation(vector):
        if len(vector)!=3 or not all(math.isfinite(v) for v in vector):
            raise ValueError('Finite XYZ unit vector required')
        if abs(sum(v*v for v in vector)-1)>1e-5:
            raise ValueError('Only unit-vector branch supported')
        x,y,z=map(f32,vector)
        projected=normalize_vector([x,y,0.0])
        if not any(projected):
            raise ValueError('Degenerate horizontal projection unsupported')
        # 1409b4ba0/4baa calls 1400369e0, including squared f32 length,
        # rounded reciprocal and separate multiplies. Double hypot/division
        # produces different dot/acos inputs near a horizontal direction.
        hx,hy=projected[:2]
        dot=f32(f32(hx*x)+f32(hy*y))
        angle=0.0 if dot>=1 else pi if dot<=-1 else f32(math.acos(dot))
        return -abs(angle) if z<0 else abs(angle)
    result=f32(elevation(first)-elevation(second))
    if result>pi:result=f32(result-two_pi)
    if result<-pi:result=f32(result+two_pi)
    if result>half_pi:result=f32(pi-result)
    if result<-half_pi:result=f32(-pi-result)
    return result
