"""Restricted float32 translation consumer140b49fb0 with native segment state."""
from jade_animation_transition import f32
from jade_pose import translation_sample


def translation_at_state(track,state):
    frames=track['frames'];index=state['frame_index']
    if not 0<=index<len(frames):raise ValueError('Frame index outside source')
    frame=frames[index];following=frames[(index+1)%len(frames)]
    transform=frame.get('transform',{})
    if transform.get('flags',0)&(8|0x40):raise ValueError('Time remapping/alternate endpoint unsupported')
    points=translation_sample(frame)
    if not points:return None
    points=[list(map(f32,p)) for p in points]
    next_points=translation_sample(following)
    if not next_points or frame['tick_raw']==0 or frame['flags']&0x800:return points[0]
    end=list(map(f32,next_points[0]));duration=f32(frame['tick_raw']/60)
    elapsed=f32(state['elapsed_seconds'])
    if elapsed<0:raise ValueError('Forward segment required')
    if elapsed>=duration:return end
    t=f32(elapsed/duration);s=f32(1-t)
    mul=lambda a,b:f32(a*b)
    add=lambda a,b:f32(a+b)
    n=len(points)
    if n==1:return [add(mul(a,s),mul(t,b)) for a,b in zip(points[0],end)]
    if n==2:
        a=mul(s,s);b=mul(add(t,t),s);c=mul(t,t)
        return [add(add(mul(b,points[1][i]),mul(points[0][i],a)),mul(c,end[i])) for i in range(3)]
    if n==3:
        a=mul(mul(s,s),s);b=mul(mul(mul(s,t),3),s)
        c=mul(mul(mul(t,3),t),s);d=mul(mul(t,t),t)
        return [add(add(add(mul(b,points[1][i]),mul(points[0][i],a)),
                            mul(c,points[2][i])),mul(d,end[i])) for i in range(3)]
    raise ValueError('Unsupported curve control count')
