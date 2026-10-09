"""Bounded stopped-left then opposite-right preview check; always release keys."""
import datetime,json,sys,time
from pathlib import Path
sys.path.insert(0,'C:/Users/Dan/.codex/plugins/cache/universal-modder/universal-modder/0.2.0')
from um.win import Drive,shot
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
driver=Drive('rebge');events=[];paused=False;error=None
def frame(name):
    global paused
    driver.key('0x50');paused=True;time.sleep(.06)
    path=f'reports/bevy/captures/standing-{name}-{stamp}.png'
    shot(path,exe='rebge.exe',scale=.5);events.append(dict(frame=name,path=path))
    driver.key('0x50');paused=False
try:
    driver.focus();driver.cmd('scanmode on');driver.key('0x52');time.sleep(.3)
    driver.key('0x41','down',pause=0.);time.sleep(1.6)
    driver.key('0x41','up',pause=0.);time.sleep(1.2);frame('stopped-left')
    driver.key('0x44','down',pause=0.);time.sleep(.2);frame('opposite-turn')
    time.sleep(.8);driver.key('0x44','up',pause=0.);time.sleep(1.);frame('completed')
except Exception as exc:
    error=repr(exc);raise
finally:
    try:
        for key in ('0x41','0x44','0x52'):driver.key(key,'up',pause=0.)
        if paused:driver.key('0x50')
    finally:driver.close()
    path=Path(f'reports/bevy/standing-input-{stamp}.json')
    path.write_text(json.dumps(dict(events=events,error=error,limits='Keyboard preview visual check; physical stick and native predicate remain unverified.'),indent=2)+'\n')
    print(path)
