"""Read-only native/physical-stick recording with audible manual-test cues."""
import argparse
import datetime
import json
import subprocess
import sys
import time
import winsound
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--pid',type=int,required=True);parser.add_argument('--base',required=True)
parser.add_argument('--resume-menu',action='store_true',help='Only after observing Return to game in the pause menu')
parser.add_argument('--duration',type=float,default=4.5,help='Active manual test window,3..7 seconds')
parser.add_argument('--label',choices=['slow','medium','fast','unspecified'],default='unspecified')
args=parser.parse_args()
if not 3.<=args.duration<=7.:parser.error('--duration must be3..7 seconds')
sys.path.insert(0,'C:/Users/Dan/.codex/plugins/cache/universal-modder/universal-modder/0.2.0')
from um.win import Drive
driver=Drive('bge');children=[];events=[];started=time.perf_counter()
try:
    driver.focus()
    if args.resume_menu:
        rect=driver.rect()
        if rect is None:raise RuntimeError('Original game window missing')
        driver.click(rect[2]*.5,rect[3]*.288)
    time.sleep(.5)
    commands=[
        [sys.executable,'tools/jade/capture_tracking_sequence.py','--pid',str(args.pid),'--base',args.base,'--samples','256','--interval-ms','25','--start-delay','3','--max-seconds',str(args.duration+.5)],
        [sys.executable,'tools/jade/probe_gamepad_input.py','--seconds',str(3.+args.duration+1.)]]
    for command in commands:
        children.append(subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True))
        events.append(dict(event='collector_started',command=command,performance_counter=time.perf_counter()))
    time.sleep(3.)
    events.append(dict(event='start_cue',performance_counter=time.perf_counter()));winsound.Beep(880,200)
    time.sleep(args.duration)
    events.append(dict(event='release_cue',performance_counter=time.perf_counter()));winsound.Beep(440,400)
    for child in children:
        stdout,stderr=child.communicate(timeout=20)
        events.append(dict(event='collector_result',returncode=child.returncode,stdout=stdout,stderr=stderr))
        print(stdout.strip())
        if child.returncode:raise RuntimeError(stderr)
finally:
    driver.close()
    for child in children:
        if child.poll() is None:child.terminate();child.wait(timeout=5)
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    path=Path(f'reports/jade/manual-gamepad-turn-{stamp}.json')
    path.write_text(json.dumps(dict(start_performance_counter=started,parameters=vars(args),events=events,
        limits=['Physical user input; no joystick or memory writes.','Cues and collector start markers are wall-clock times, not atomic native callbacks.']),indent=2)+'\n')
    print(path)
