"""Visual reverse-input preview check; source clips, approximate selection."""
import datetime,json,sys,time
from pathlib import Path
sys.path.insert(0,'C:/Users/Dan/.codex/plugins/cache/universal-modder/universal-modder/0.2.0')
from um.win import Drive,shot
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
driver=Drive('rebge'); events=[]; error=None
def frame(name):
    # Freeze the preview so screenshot overhead does not skip the short turn pose.
    driver.key('0x50');time.sleep(.05)
    path=f'reports/bevy/captures/reverse-{name}-{stamp}.png'
    shot(path,exe='rebge.exe',scale=.5)
    events.append(dict(frame=name,path=path))
    driver.key('0x50')
try:
    driver.focus();driver.cmd('scanmode on');driver.key('0x52');time.sleep(.2)
    driver.key('0x57','down',pause=0.);time.sleep(1.6)
    driver.key('0x57','up',pause=0.);driver.key('0x53','down',pause=0.)
    time.sleep(.12);frame('early')
    time.sleep(.35);frame('held')
    driver.key('0x53','up',pause=0.);time.sleep(1.);frame('released')
    driver.key('0x52');time.sleep(.2)
    driver.key('0x57','down',pause=0.);time.sleep(1.6)
    driver.key('0x57','up',pause=0.);driver.key('0x53','down',pause=0.)
    time.sleep(.12);driver.key('0x53','up',pause=0.)
    time.sleep(.6);frame('stop-exit')
    time.sleep(.8);frame('stopped')
except Exception as exc:
    error=repr(exc);raise
finally:
    try:
        for key in ('0x57','0x53','0x52'):driver.key(key,'up',pause=0.)
    finally:driver.close()
    report=Path(f'reports/bevy/reverse-input-{stamp}.json')
    report.write_text(json.dumps(dict(events=events,error=error,limitations=[
        'Screenshot timing is external and may skip clip phases; runtime logs and tests supplement visual checks.']),indent=2)+'\n')
    print(report)
