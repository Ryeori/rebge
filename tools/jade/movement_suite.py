"""Declarative DS4 timelines shared by native and REBGE measurement runners."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / 'tools/jade/movement_cases.json'

def point(t, x=0., y=0., r2=0.):
    return dict(t=round(t,4), x=x, y=y, r2=r2)

def build_catalog():
    cases=[]
    def add(name, category, points, checks, priority=1, terrain='flat_open'):
        end=points[-1]['t']
        cases.append(dict(id=name,category=category,priority=priority,terrain=terrain,
            setup='face_left_rest', repetitions=3,
            duration=round(end+.9,4), points=points,
            checks=checks, status='pending'))
    for magnitude in [.10,.14,.16,.20,.25,.30,.35,.50,.65,1.]:
        add(f'strength_{magnitude:.2f}','input_threshold',
            [point(0),point(.15,0,magnitude),point(1.,0,magnitude),point(1.01)],
            ['movement onset','selected gait','input normalization','neutral recovery'])
    for rise in [0.,.10,.20,.35,.70]:
        add(f'start_rise_{rise:.2f}','start',
            [point(0),point(.05),point(.05+max(rise,.01),0,1),point(1.3+rise,0,1),point(1.31+rise)],
            ['idle/slow/start/walk chain','time to stable speed','actor acceleration'])
    for rise in [0.,.10,.20,.35,.70]:
        for side in ['left','right']:
            # Setup left. Right-facing preparation is a mirrored setup.
            sign=1. if side=='right' else -1.
            add(f'standing_{side}_rise_{rise:.2f}','standing_turn',
                [point(0),point(.05),point(.05+max(rise,.01),sign),point(.20+rise,sign),point(.21+rise)],
                ['116/117 selection','completion after release','final heading','idle blend continuity'])
            cases[-1]['setup']='face_left_rest' if side=='right' else 'face_right_rest'
    for hold in [.05,.12,.25,.35,.50,.75]:
        add(f'standing_release_{hold:.2f}','standing_release',
            [point(0),point(.01,1),point(.01+hold,1),point(.02+hold)],
            ['release during entry/body/exit','turn completion','outgoing terminal pose'])
    for angle in [45,90,120,150,170,180]:
        for side in [-1,1]:
            # Actor initially left; positive x is opposite. Angle is relative to facing.
            theta=math.radians(angle)
            x=-math.cos(theta); y=side*math.sin(theta)
            add(f'angle_{angle}_{"cw" if side<0 else "ccw"}','turn_angle',
                [point(0),point(.01,x,y),point(.55,x,y),point(.56)],
                ['standing turn angle gate','turn side','heading error'],priority=2)
    for mode in ['walk_stop','run_stop','run_to_walk','walk_to_run','run_held_start']:
        if mode=='walk_stop': pts=[point(0),point(.01,0,1),point(1.3,0,1),point(1.31)]
        elif mode=='run_stop': pts=[point(0),point(.01,0,1,1),point(2.,0,1,1),point(2.01)]
        elif mode=='run_to_walk': pts=[point(0),point(.01,0,1,1),point(1.3,0,1,1),point(1.31,0,1),point(2.1,0,1),point(2.11)]
        elif mode=='walk_to_run': pts=[point(0),point(.01,0,1),point(.8,0,1),point(.81,0,1,1),point(1.8,0,1,1),point(1.81)]
        else: pts=[point(0,0,0,1),point(.35,0,0,1),point(.36,0,1,1),point(1.8,0,1,1),point(1.81)]
        add(mode,'gait',pts,['action/phase chain','speed byte','actor speed profile','pose discontinuity'])
    for hold in [.50,1.30,2.80]:
        add(f'run_reverse_{hold:.2f}','run_reverse',
            [point(0),point(.01,0,1,1),point(.01+hold,0,1,1),point(.02+hold,0,-1,1),
             point(1.82+hold,0,-1,1),point(1.83+hold)],
            ['79 A/B then80 then2','post-turn acceleration','backward model displacement','incoming blend'])
    for hold in [.10,.20,.30,.45]:
        add(f'walk_reverse_short_{hold:.2f}', 'walk_reverse',
            [point(0), point(.15,-1), point(.15+hold,-1),
             point(.16+hold,1), point(1.36+hold,1), point(1.37+hold)],
            ['actual speed10D4 and action before reversal',
             'minimal no-shift acceleration before79 versus standing116',
             'opposite delivery and current facing gate', 'blend/pending timing',
             'old-direction inertia and neutral recovery'])
    add('walk_reverse_steady_no_shift','walk_reverse',
        [point(0),point(.15,-1),point(1.65,-1),point(1.66,1),
         point(3.16,1),point(3.17)],
        ['qualified steady action3 before opposite input','reverse onset and79 A/B then80 then3',
         'old-direction displacement after opposite input','raw norm and filtered direction',
         'mode34 and speed10D4','velocity flags and source blend','post-turn walking acceleration'])
    for gap in [.05,.15,.30,.70,1.60,2.20]:
        add(f'reentry_gap_{gap:.2f}','stop_reentry',
            [point(0),point(.01,0,1),point(.61,0,1),point(.62),point(.62+gap),
             point(.63+gap,0,1),point(1.3+gap,0,1),point(1.31+gap)],
            ['stop interruption','idle versus waiting path','queued target','speed continuity'])
    for at in [.08,.20,.35]:
        add(f'turn_redirect_{at:.2f}','interrupt',
            [point(0),point(.01,1),point(.01+at,1),point(.02+at,0,1),point(.8,0,1),point(.81)],
            ['direction change during turn','queued movement','completion or interruption'])
    for drift in [.05,.10,.14,.16]:
        add(f'release_rebound_{drift:.2f}','noise',
            [point(0),point(.01,0,1,1),point(1.,0,1,1),point(1.01),point(1.04,0,-drift),
             point(1.10),point(1.14,0,-drift),point(1.20)],
            ['false reverse on release','deadzone','neutral stability'])
    for direction in [(0,1),(.707106,.707106)]:
        tag='head_on' if direction[0]==0 else 'oblique'
        add(f'wall_{tag}','collision',[point(0),point(.01,*direction,1),point(1.5,*direction,1),point(1.51)],
            ['blocked actor movement','slow animation against wall','sliding'],priority=3,terrain='wall_prepared')
    add('camera_relative_forward','camera', [point(0),point(.01,0,1),point(1.,0,1),point(1.01)],
        ['movement basis after manual camera rotation'],priority=3)
    validate(dict(schema='rebge-movement-suite-v1',cases=cases))
    return dict(schema='rebge-movement-suite-v1',sample_hz=100,
        rules=['One case per scene readiness; no unattended terrain-dependent batch.',
               'Reset camera and facing, neutral >=1.2s; validate actual native idle before input.',
               'Three independent repeats; add near-boundary probes only for measured disagreements.',
               'Original source units; no claim of collision parity in open-ground tests.'],cases=cases)

def validate(catalog):
    ids=set()
    for c in catalog['cases']:
        if c['id'] in ids: raise ValueError('Duplicate case ID')
        ids.add(c['id'])
        pts=c['points']
        if not 0< c['duration'] <=6.5: raise ValueError(f'Unbounded duration: {c["id"]}')
        if not pts or pts[0]['t']!=0: raise ValueError('Missing timeline origin')
        for i,p in enumerate(pts):
            if not all(math.isfinite(p[k]) for k in ('t','x','y','r2')): raise ValueError('Nonfinite input')
            if i and p['t']<=pts[i-1]['t']: raise ValueError('Timeline not strictly increasing')
            if math.hypot(p['x'],p['y'])>1.000001 or not 0<=p['r2']<=1: raise ValueError('Invalid input range')
        if any(pts[-1][k] for k in ('x','y','r2')): raise ValueError('Missing final neutral')

def evaluate(points,t):
    if t<=points[0]['t']: return {k:points[0][k] for k in ('x','y','r2')}
    for a,b in zip(points,points[1:]):
        if t<=b['t']:
            r=(t-a['t'])/(b['t']-a['t'])
            return {k:a[k]+r*(b[k]-a[k]) for k in ('x','y','r2')}
    return {k:points[-1][k] for k in ('x','y','r2')}

if __name__=='__main__':
    CATALOG.write_text(json.dumps(build_catalog(),indent=2)+'\n')
    print(CATALOG)
