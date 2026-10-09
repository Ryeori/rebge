"""Exercise only the REBGE preview window; release keys even on failure."""
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
start = time.perf_counter()
error = None
try:
    driver.focus()
    driver.cmd('scanmode on')
    driver.key('0x52', 'down', pause=0.)
    driver.key('0x52', 'up', pause=0.)
    time.sleep(.3)
    for name,key in [('W','0x57'),('D','0x44'),('S','0x53'),('A','0x41')]:
        events.append(dict(command=name+' down',at=time.perf_counter()-start))
        driver.key(key,'down',pause=0.)
        time.sleep(1.25)
        path=f'reports/bevy/captures/steering-{name}-{stamp}.png'
        shot(path,exe='rebge.exe',scale=.5)
        events.append(dict(command=name+' screenshot',at=time.perf_counter()-start,path=path))
        driver.key(key,'up',pause=0.)
        events.append(dict(command=name+' up',at=time.perf_counter()-start))
        time.sleep(.2)
    time.sleep(1.)
    path=f'reports/bevy/captures/steering-stopped-{stamp}.png'
    shot(path,exe='rebge.exe',scale=.5)
    events.append(dict(command='stopped screenshot',at=time.perf_counter()-start,path=path))
except Exception as exc:
    error=repr(exc)
    raise
finally:
    try:
        for key in ('0x57','0x44','0x53','0x41','0x52'):
            driver.key(key,'up',pause=0.)
    finally:
        driver.close()
    report=Path(f'reports/bevy/steering-input-{stamp}.json')
    report.write_text(json.dumps(dict(events=events,error=error,
        limitations=['External wall-time commands; screenshots are visual checks, not native timing parity.']),indent=2)+'\n')
    print(str(report))
