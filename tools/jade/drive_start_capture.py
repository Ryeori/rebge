"""User-authorized short W test; WinDrive foreground guard and final key release."""
import datetime
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--pid', type=int, required=True)
parser.add_argument('--base', required=True)
parser.add_argument('--restart', action='store_true', help='Second W press after stop, within idle0 window')
parser.add_argument('--loaded', action='store_true', help='Previously observed loaded scene; do not click pause menu')
parser.add_argument('--pulse', action='store_true', help='50ms W pulse to observe release while blend is active')
parser.add_argument('--restart-gap', type=float, default=1.65, help='Seconds between release and second W press')
parser.add_argument('--waiting-repress', action='store_true', help='Pulse, then W during incoming waiting-idle blend')
parser.add_argument('--turn', action='store_true', help='Short W then D change to observe angular speed inputs')
parser.add_argument('--reverse', action='store_true', help='W then opposite S input to observe fast-turn selection')
parser.add_argument('--slow-turn', action='store_true', help='80ms W then S: inspect turn selection before walking')
parser.add_argument('--run', action='store_true', help='W -> Shift+W -> W: distinguish locomotion branches')
parser.add_argument('--run-release', action='store_true', help='Sustained Shift+W, release both: inspect run stopping')
parser.add_argument('--run-release-hold', type=float, default=2.8, help='Sprint before full release, bounded .5..3s')
parser.add_argument('--run-reverse', action='store_true', help='W then Shift+W1s, then Shift+S600ms')
parser.add_argument('--run-reverse-after', type=float, default=.6, help='Hold opposite running input .6..2.2s to observe acceleration after turn')
parser.add_argument('--run-reverse-hold',type=float,default=1.,help='Running before reverse; bounded0.5..3s')
parser.add_argument('--reverse-hold',type=float,default=.6,help='Opposite input duration; bounded .2..2s')
parser.add_argument('--reverse-repress',action='store_true',help='After opposite release, wait150ms then hold opposite again600ms')
parser.add_argument('--speed-observer', action='store_true', help='Use narrow readonly speed publication observer')
args = parser.parse_args()
if not .2 <= args.reverse_hold <= 2.:
    parser.error('--reverse-hold must be .2..2 seconds')
if not .6 <= args.run_reverse_after <= 2.2:
    parser.error('--run-reverse-after must be .6..2.2 seconds')
if not .5 <= args.run_reverse_hold <= 3.:
    parser.error('--run-reverse-hold must be .5..3 seconds')
if not .5 <= args.run_release_hold <= 3.:
    parser.error('--run-release-hold must be .5..3 seconds')
if args.slow_turn:
    args.reverse = True
if args.reverse:
    args.turn = True
if args.reverse_repress and not args.reverse:
    parser.error('--reverse-repress requires --reverse')
if args.run_release or args.run_reverse:
    args.run = True
if args.run and (args.turn or args.restart or args.pulse or args.waiting_repress):
    parser.error('--run requires a separate locomotion test')
if args.turn and (args.restart or args.pulse or args.waiting_repress):
    parser.error('--turn cannot be combined with restart/pulse/waiting-repress')
if args.pulse and args.restart:
    parser.error('--pulse and --restart are mutually exclusive')
if not .05 <= args.restart_gap <= 2.:
    parser.error('--restart-gap must be between .05 and2 seconds')
if args.waiting_repress:
    if args.pulse or args.restart:
        parser.error('--waiting-repress cannot be combined with --pulse or --restart')
    args.pulse=True
    args.restart=True
    args.restart_gap=2.2
sys.path.insert(0, 'C:/Users/Dan/.codex/plugins/cache/universal-modder/universal-modder/0.2.0')
from um.win import Drive, shot

driver = Drive('bge')
capture = None
actions = []
stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
started = time.perf_counter()
capture_report = None
try:
    driver.focus()
    driver.cmd('scanmode on')
    # The observed pause menu has Return to game at normalized client(.5,.288).
    rect = driver.rect()
    if rect is None:
        raise RuntimeError('Game window missing')
    left, top, width, height = rect
    if not args.loaded:
        actions.append(dict(command='resume observed menu', at=time.perf_counter()-started))
        driver.click(width * .5, height * .288)
    time.sleep(2.5 if args.slow_turn else 1.)
    shot(f'reports/bevy/captures/native-auto-start-before-{stamp}.png', exe='bge.exe', scale=.33)
    capture_args = ([sys.executable, 'tools/jade/capture_speed_order.py', '--pid', str(args.pid), '--base', args.base]
        if args.speed_observer else [sys.executable, 'tools/jade/capture_tracking_sequence.py',
        '--pid', str(args.pid), '--base', args.base, '--samples', '256',
        '--interval-ms', '25' if args.restart or args.reverse or args.run else '10', '--start-delay', '0'])
    if args.run_reverse and not args.speed_observer:
        capture_args += ['--max-seconds', str(min(8., .45 + .6 + args.run_reverse_hold + args.run_reverse_after + .6))]
    elif args.run_release and not args.speed_observer:
        capture_args += ['--max-seconds', str(min(8., .45 + .6 + args.run_release_hold + 2.2))]
    capture = subprocess.Popen(capture_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(.45)
    actions.append(dict(command='W down', at=time.perf_counter()-started))
    driver.key('0x57', 'down', pause=0.)
    time.sleep(.6 if args.run else .08 if args.slow_turn else .05 if args.pulse else 1.0 if args.reverse else .6 if args.turn else 1.25)
    if args.run:
        driver.key('0x10', 'down', pause=0.)
        actions.append(dict(command='Shift down; W held', at=time.perf_counter()-started))
        time.sleep(args.run_reverse_hold if args.run_reverse else args.run_release_hold if args.run_release else .8)
        if args.run_reverse:
            driver.key('0x57','up',pause=0.)
            actions.append(dict(command='W up; Shift held',at=time.perf_counter()-started))
            driver.key('0x53','down',pause=0.)
            actions.append(dict(command='S down; Shift held',at=time.perf_counter()-started))
            time.sleep(args.run_reverse_after)
            driver.key('0x53','up',pause=0.)
            actions.append(dict(command='S up',at=time.perf_counter()-started))
        elif args.run_release:
            driver.key('0x57', 'up', pause=0.)
            actions.append(dict(command='W up; Shift held', at=time.perf_counter()-started))
        driver.key('0x10', 'up', pause=0.)
        actions.append(dict(command='Shift up; movement released' if args.run_release or args.run_reverse
            else 'Shift up; W held', at=time.perf_counter()-started))
        if not args.run_release and not args.run_reverse:
            time.sleep(.6)
    driver.key('0x57', 'up', pause=0.)
    actions.append(dict(command='W up', at=time.perf_counter()-started))
    if args.turn:
        turn_name, turn_key = ('S', '0x53') if args.reverse else ('D', '0x44')
        actions.append(dict(command=turn_name+' down', at=time.perf_counter()-started))
        driver.key(turn_key, 'down', pause=0.)
        time.sleep(args.reverse_hold if args.reverse else .6)
        driver.key(turn_key, 'up', pause=0.)
        actions.append(dict(command=turn_name+' up', at=time.perf_counter()-started))
        if args.reverse_repress:
            time.sleep(.15)
            actions.append(dict(command=turn_name+' down second',at=time.perf_counter()-started))
            driver.key(turn_key,'down',pause=0.)
            time.sleep(.6)
            driver.key(turn_key,'up',pause=0.)
            actions.append(dict(command=turn_name+' up second',at=time.perf_counter()-started))
    if args.restart:
        time.sleep(args.restart_gap)
        actions.append(dict(command='W down second', at=time.perf_counter()-started))
        driver.key('0x57', 'down', pause=0.)
        time.sleep(1.25)
        driver.key('0x57', 'up', pause=0.)
        if args.run:
            driver.key('0x10', 'up', pause=0.)
        actions.append(dict(command='W up second', at=time.perf_counter()-started))
    stdout, stderr = capture.communicate(timeout=30)
    print(stdout)
    if capture.returncode:
        raise RuntimeError(stderr)
    if stdout.strip():
        capture_report = json.loads(stdout.strip().splitlines()[-1]).get('report')
    shot(f'reports/bevy/captures/native-auto-start-after-{stamp}.png', exe='bge.exe', scale=.33)
finally:
    try:
        driver.key('0x57', 'up', pause=0.)
        if args.run:
            driver.key('0x10','up',pause=0.)
        if args.run_reverse:
            driver.key('0x53','up',pause=0.)
        if args.turn:
            driver.key('0x44', 'up', pause=0.)
            driver.key('0x53', 'up', pause=0.)
    finally:
        driver.close()
    Path(f'reports/jade/stage43-auto-start-input-{stamp}.json').write_text(
        json.dumps(dict(actions=actions, start_performance_counter=started,
            parameters=vars(args), capture_report=capture_report,
            capture_complete=capture is not None and capture.poll()==0,
            limitations=['Input command timestamps are external wall time, not native callback times.']), indent=2)+'\n')
