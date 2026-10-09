"""User-authorized virtual left stick; guarded focus and neutral cleanup."""
import argparse
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--pid',type=int,required=True)
p.add_argument('--base',required=True)
p.add_argument('--resume-menu',action='store_true')
p.add_argument('--rise',type=float,default=.2)
p.add_argument('--device',choices=['xbox','ds4'],default='xbox')
p.add_argument('--preview',action='store_true')
a=p.parse_args()
if not 0 <= a.rise <= .7:
    p.error('--rise must be 0..0.7 seconds')
sys.path.insert(0,str(Path('tools/game-automation/python/vgamepad-0.1.0').resolve()))
sys.path.insert(0,'C:/Users/Dan/.codex/plugins/cache/universal-modder/universal-modder/0.2.0')
import vgamepad
from um.win import Drive, shot

stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
events=[]
collectors=[]
results=[]
error=None
pad=vgamepad.VX360Gamepad() if a.device=='xbox' else vgamepad.VDS4Gamepad()
target='rebge' if a.preview else 'bge'
d=Drive(target)
def axis(x):
    # Virtual HID is system-wide: refuse non-neutral input after focus loss.
    if x and d.cmd('fg').lower() != target:
        raise RuntimeError('Original lost foreground; aborting virtual input')
    pad.left_joystick_float(x_value_float=x,y_value_float=0.)
    pad.update()
    events.append(dict(performance_counter=time.perf_counter(),left_x=x,left_y=0.))
def ramp(x):
    if a.rise == 0:
        axis(x)
        return
    origin=time.perf_counter()
    while True:
        t=min(1.,(time.perf_counter()-origin)/a.rise)
        axis(x*t)
        if t==1.: break
        time.sleep(.01)
try:
    pad.reset();pad.update()
    d.focus()
    rect=d.rect()
    if rect is None: raise RuntimeError('Original window missing')
    if a.resume_menu: d.click(rect[2]*.5,rect[3]*.288)
    if a.preview:
        d.key('0x52','tap',pause=0.)
    time.sleep(1.)
    axis(-1.);time.sleep(.7);axis(0.);time.sleep(1.2)
    shot(f'reports/bevy/captures/{target}-analog-before-{stamp}.png',exe=target+'.exe',scale=.33)
    commands=[
        [sys.executable,'tools/jade/capture_tracking_sequence.py','--pid',str(a.pid),'--base',a.base,
         '--samples','256','--interval-ms','25','--start-delay','0','--max-seconds','7.5'],
        [sys.executable,'tools/jade/probe_gamepad_input.py','--seconds','8']]
    if a.preview: commands=commands[1:]
    for command in commands:
        collectors.append((command,subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)))
    time.sleep(.4)
    for x in [1.,-1.,1.,-1.]:
        foreground=d.cmd('fg')
        events.append(dict(foreground=foreground,performance_counter=time.perf_counter()))
        ramp(x);time.sleep(.15);axis(0.);time.sleep(.9)
    for command,child in collectors:
        out,err=child.communicate(timeout=20)
        results.append(dict(command=command,returncode=child.returncode,stdout=out,stderr=err))
        if child.returncode: raise RuntimeError(err)
    shot(f'reports/bevy/captures/{target}-analog-after-{stamp}.png',exe=target+'.exe',scale=.33)
except Exception as exc:
    error=repr(exc)
    raise
finally:
    pad.reset();pad.update()
    d.close()
    for _,child in collectors:
        if child.poll() is None:child.terminate()
    output=Path(f'reports/jade/analog-standing-input-{stamp}.json')
    output.write_text(json.dumps(dict(parameters=vars(a),events=events,collectors=results,error=error,
        limits=['Virtual HID input is system-wide; no native memory writes.',
                'External wall clocks and sequential native reads are not atomic.']),indent=2)+'\n')
    print(json.dumps(dict(report=str(output),collectors=results,error=error)))
