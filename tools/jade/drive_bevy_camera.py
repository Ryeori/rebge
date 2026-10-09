"""Short preview camera check; release held keys/buttons even on failure."""
import datetime
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, 'C:/Users/Dan/.codex/plugins/cache/universal-modder/universal-modder/0.2.0')
from um.win import Drive, shot

stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
driver = Drive('rebge')
events = []
error = None
def frame(name):
    path = f'reports/bevy/captures/camera-{name}-{stamp}.png'
    shot(path, exe='rebge.exe', scale=.5)
    events.append(dict(frame=name, path=path))
try:
    driver.focus()
    driver.cmd('scanmode on')
    time.sleep(.3)
    frame('before')
    driver.key('0x27', 'down', pause=0.)
    time.sleep(.8)
    driver.key('0x27', 'up', pause=0.)
    time.sleep(.2)
    frame('arrow-right')
    driver.key('0x24')
    time.sleep(.2)
    frame('home')
    if '--mouse' in sys.argv:
        driver.cmd('move 640 360')
        driver.cmd('mdown 640 360 right')
        for _ in range(6):
            driver.cmd('rel 30 -8')
            time.sleep(.04)
        driver.cmd('mup right')
        time.sleep(.2)
        frame('mouse-orbit')
        driver.cmd('wheel 240')
        time.sleep(.2)
        frame('wheel-zoom')
except Exception as exc:
    error = repr(exc)
    raise
finally:
    try:
        driver.key('0x27', 'up', pause=0.)
        driver.key('0x24', 'up', pause=0.)
        driver.cmd('mup right')
    finally:
        driver.close()
    output = Path(f'reports/bevy/camera-input-{stamp}.json')
    output.write_text(json.dumps(dict(events=events, error=error,
        limitations=['Preview UI test, no native camera parity claim']), indent=2)+'\n')
    print(output)
