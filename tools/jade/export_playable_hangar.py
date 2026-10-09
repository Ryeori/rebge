"""Compose existing private exports; spawn selection is a preview policy."""
import argparse
import hashlib
import json
from pathlib import Path
from project_paths import PROJECT_ROOT

p=argparse.ArgumentParser()
p.add_argument('--x',type=float,default=70.0882617632548)
p.add_argument('--y',type=float,default=10.917366325855255)
p.add_argument('--max-height',type=float,default=1.2)
p.add_argument('--find-floor',action='store_true')
p.add_argument('--floor-object',default='1F0000C6')
a=p.parse_args()
environment_path=PROJECT_ROOT/'assets/scenes/D90057F0/scene.json'
actor_path=PROJECT_ROOT/'assets/scenes/sally-playback/controlled-scene.json'
environment=json.loads(environment_path.read_text())
actor=json.loads(actor_path.read_text())
hits=[]
if a.find_floor:
    candidates=[]
    for batch in environment['batches']:
        if batch['object']=='D90057F2':continue
        if a.floor_object and batch['object']!=a.floor_object:continue
        vertices=batch['vertices']
        for offset in range(0,len(vertices),15):
            v=[vertices[offset+i:offset+i+3] for i in (0,5,10)]
            e=[[v[j][i]-v[0][i] for i in range(3)] for j in (1,2)]
            n=[e[0][1]*e[1][2]-e[0][2]*e[1][1],e[0][2]*e[1][0]-e[0][0]*e[1][2],e[0][0]*e[1][1]-e[0][1]*e[1][0]]
            size=sum(x*x for x in n)**.5
            center=[sum(p[i] for p in v)/3 for i in range(3)]
            if size>.4 and abs(n[2])/size>.85 and 0<center[2]<a.max_height:
                candidates.append(dict(object=batch['object'],mesh=batch['mesh'],position=center,
                    distance=((center[0]-a.x)**2+(center[1]-a.y)**2)**.5,area=size/2))
    candidates.sort(key=lambda c:c['distance'])
    print(json.dumps(candidates[:12],indent=2))
    raise SystemExit(0)
for batch in environment['batches']:
    # User identifies this as hangar water. Type5 first-layer red texture does
    # not reconstruct its native shader, and water is not a spawn floor.
    if batch['object']=='D90057F2':continue
    if a.floor_object and batch['object']!=a.floor_object:continue
    vertices=batch['vertices']
    for offset in range(0,len(vertices),15):
        v=[vertices[offset+i:offset+i+3] for i in (0,5,10)]
        x0,y0,z0=v[0];x1,y1,z1=v[1];x2,y2,z2=v[2]
        determinant=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
        if abs(determinant)<1e-8:continue
        nx=(y1-y0)*(z2-z0)-(z1-z0)*(y2-y0)
        ny=(z1-z0)*(x2-x0)-(x1-x0)*(z2-z0)
        nz=(x1-x0)*(y2-y0)-(y1-y0)*(x2-x0)
        if abs(nz)/(nx*nx+ny*ny+nz*nz)**.5<.7:continue
        u=((y1-y2)*(a.x-x2)+(x2-x1)*(a.y-y2))/determinant
        w=((y2-y0)*(a.x-x2)+(x0-x2)*(a.y-y2))/determinant
        if min(u,w,1-u-w)<-1e-6:continue
        z=u*z0+w*z1+(1-u-w)*z2
        if -1<=z<=a.max_height:
            hits.append(dict(z=z,object=batch['object'],mesh=batch['mesh'],triangle=offset//15))
if not hits:raise ValueError('No candidate floor; choose a measured hangar point')
floor=max(hits,key=lambda h:h['z'])
scene=dict(actor)
scene['name']='Jade in source hangar · playable preview'
scene['batches']=environment['batches']+actor['batches']
for batch in scene['batches']:
    if batch['object']=='D90057F2':batch['preview_water']=True
scene['actor_spawn']=[a.x,floor['z']+.03,-a.y]
scene['preview_camera']=dict(target=[a.x,floor['z']+.8,-a.y],distance=4.5,yaw=.8-3.141592653589793,pitch=.3)
scene['limits']=actor.get('limits','')+' WASD steering/camera mapping and translucent water material are preview approximations. Water identity supplied by user. Spawn is a visual triangle-height policy; no collision, gravity or water physics.'
destination=PROJECT_ROOT/'assets/scenes/sally-hangar/scene.json'
destination.parent.mkdir(parents=True,exist_ok=True)
destination.write_text(json.dumps(scene,separators=(',',':')))
report=dict(scene=str(destination.relative_to(PROJECT_ROOT)),floor=floor,spawn=scene['actor_spawn'],
    batches=len(scene['batches']),inputs=[dict(path=str(path.relative_to(PROJECT_ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in (environment_path,actor_path)],
    water=dict(object='D90057F2',material='0C018705',identity='User identifies hangar water',preview='Translucent tint; native shader and water physics not recovered'),
    limitations=['Source visible triangles do not establish native collision surfaces.','Spawn/steering/camera placement and water appearance are preview policies.'])
output=PROJECT_ROOT/'reports/bevy/playable-hangar-export-20261009.json'
output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
