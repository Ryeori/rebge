"""Bounded A/D reversals from rest; external timestamps and readonly native trace."""
import argparse
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--pid', type=int, required=True)
p.add_argument('--base', required=True)
p.add_argument('--resume-menu', action='store_true')
p.add_argument('--hold', type=float, default=.5)
a = p.parse_args()
if not .12 <= a.hold <= .65:
    p.error('--hold must be .12..65 seconds')
sys.path.insert(0, 'C:/Users/Dan/.codex/plugins/cache/universal-modder/universal-modder/0.2.0')
from um.win import Drive, shot

stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
started = time.perf_counter()
events = []
collector = None
result = None
d = Drive('bge')
def key(name, vk, state):
    events.append(dict(command=f'{name} {state}', performance_counter=time.perf_counter()))
    d.key(vk, state, pause=0.)
try:
    d.focus()
    d.cmd('scanmode on')
    rect = d.rect()
    if rect is None:
        raise RuntimeError('Original window missing')
    if a.resume_menu:
        d.click(rect[2]*.5, rect[3]*.288)
    time.sleep(.8)
    # Establish camera-relative left heading, then allow a complete stop.
    key('A','0x41','down')
    time.sleep(.65)
    key('A','0x41','up')
    time.sleep(1.2)
    shot(f'reports/bevy/captures/native-standing-key-before-{stamp}.png', exe='bge.exe', scale=.33)
    command = [sys.executable,'tools/jade/capture_tracking_sequence.py','--pid',str(a.pid),
        '--base',a.base,'--samples','256','--interval-ms','25','--start-delay','0','--max-seconds','7.5']
    collector = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    time.sleep(.4)
    for name,vk in [('D','0x44'),('A','0x41'),('D','0x44'),('A','0x41')]:
        key(name,vk,'down')
        time.sleep(a.hold)
        key(name,vk,'up')
        time.sleep(1.)
    out,err = collector.communicate(timeout=20)
    result = dict(returncode=collector.returncode,stdout=out,stderr=err,command=command)
    if collector.returncode:
        raise RuntimeError(err)
    shot(f'reports/bevy/captures/native-standing-key-after-{stamp}.png', exe='bge.exe', scale=.33)
finally:
    try:
        key('A','0x41','up')
        key('D','0x44','up')
    finally:
        d.close()
        if collector is not None and collector.poll() is None:
            collector.terminate()
        path = Path(f'reports/jade/standing-keyboard-input-{stamp}.json')
        path.write_text(json.dumps(dict(parameters=vars(a),start_performance_counter=started,
            events=events,collector=result,limits=['Digital input cannot measure analogue rise time.',
            'Sequential native reads are not atomic; qualify transitions independently.']),indent=2)+'\n')
        print(json.dumps(dict(input_report=str(path),collector=result)))
