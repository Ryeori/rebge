"""Short preview walk/run/stop check; release inputs on exit."""
import datetime
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,'C:/Users/Dan/.codex/plugins/cache/universal-modder/universal-modder/0.2.0')
from um.win import Drive,shot
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
driver=Drive('rebge'); events=[]; error=None; paused=False
def frame(name):
    global paused
    driver.key('0x50'); paused=True; time.sleep(.05)
    path=f'reports/bevy/captures/run-{name}-{stamp}.png'
    shot(path,exe='rebge.exe',scale=.5)
    events.append(dict(name=name,path=path))
    driver.key('0x50'); paused=False
try:
    driver.focus();driver.cmd('scanmode on');driver.key('0x52');time.sleep(.2)
    driver.key('0x57','down',pause=0.);time.sleep(1.5);frame('walk')
    driver.key('0x10','down',pause=0.);time.sleep(.6);frame('running')
    driver.key('0x10','up',pause=0.);time.sleep(.6);frame('walk-again')
    driver.key('0x57','up',pause=0.);time.sleep(1.5);frame('stopped')
except Exception as exc:
    error=repr(exc);raise
finally:
    try:
        for key in ('0x57','0x10'):driver.key(key,'up',pause=0.)
        if paused:driver.key('0x50')
    finally:driver.close()
    report=Path(f'reports/bevy/run-input-{stamp}.json')
    report.write_text(json.dumps(dict(events=events,error=error,limits=['External key timing and paused screenshots do not prove native frame parity.']),indent=2)+'\n')
    print(report)
