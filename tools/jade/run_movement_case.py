"""Run one bounded DS4 timeline; scene readiness is explicit, no blind batches."""
import argparse
import ctypes
import datetime
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from movement_suite import ROOT, CATALOG, evaluate, validate
from movement_readiness import wait_ready, NativeState

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--case',required=True)
    p.add_argument('--target',choices=['original','preview'],required=True)
    p.add_argument('--scene-ready',action='store_true')
    p.add_argument('--terrain',choices=['flat_open','wall_prepared'],default='flat_open')
    p.add_argument('--resume-menu',action='store_true')
    p.add_argument('--require-opposite',action='store_true',help='Original standing ramp: audit setup geometry and abort incorrect initial direction')
    p.add_argument('--repeat',type=int,choices=[1,2,3],default=1)
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--preview-trace',type=Path)
    a=p.parse_args()
    catalog=json.loads(CATALOG.read_text());validate(catalog)
    case=next((c for c in catalog['cases'] if c['id']==a.case),None)
    if case is None:p.error('Unknown case ID')
    if a.dry_run:
        print(json.dumps(dict(case=case,samples=[dict(t=round(i/100,3),**evaluate(case['points'],i/100))
              for i in range(int(case['duration']*100)+1)]),indent=2));return
    if not a.scene_ready:p.error('Observe loaded scene first, then pass --scene-ready')
    if a.terrain!=case['terrain']:p.error('Required terrain is not prepared')
    if a.target=='preview' and not a.preview_trace:p.error('Provide active REBGE_MOVEMENT_TRACE file')
    if a.require_opposite and (a.target!='original' or case['category']!='standing_turn'):
        p.error('Opposite geometry guard requires original standing-turn case')
    from automation_paths import configure_imports
    configure_imports()
    import vgamepad
    from um.win import Drive, shot
    target='bge' if a.target=='original' else 'rebge'
    # Fresh exact process identity; generic UM bge matching is ambiguous with REBGE.
    cmd="Get-Process | Where-Object { $_.ProcessName -in @('bge','rebge') } | ForEach-Object { [pscustomobject]@{name=$_.ProcessName;pid=$_.Id;base=$_.MainModule.BaseAddress.ToInt64()} } | ConvertTo-Json -Compress"
    processes=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',cmd],text=True,timeout=20))
    if isinstance(processes,dict):processes=[processes]
    if target=='bge' and any(q['name']=='rebge' for q in processes):
        raise RuntimeError('Close preview before original capture: UM bge target is ambiguous')
    proc=next(q for q in processes if q['name']==target)
    foreground=ctypes.windll.user32.GetForegroundWindow
    foreground.restype=ctypes.c_void_p
    getpid=ctypes.windll.user32.GetWindowThreadProcessId
    getpid.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
    def guard():
        pid=ctypes.c_ulong();getpid(foreground(),ctypes.byref(pid))
        if pid.value!=proc['pid']:raise RuntimeError('Target lost foreground; neutralizing controller')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    output=ROOT/'reports/jade/movement-suite'/f'{a.case}-{a.target}-r{a.repeat}-{stamp}'
    output.mkdir(parents=True)
    driver=None;pad=None;children=[];events=[];results=[];error=None;geometry_reader=None
    report=dict(schema='movement-case-run-v1',case=case,parameters=vars(a)|{'preview_trace':str(a.preview_trace) if a.preview_trace else None},
        process=proc,catalog_sha256=hashlib.sha256(CATALOG.read_bytes()).hexdigest(),output=str(output),
        limits=['Sequential native reads are not atomic callbacks.','Identical commands do not prove identical delivered input; inspect controller record.',
                'Initial facing/camera, native idle and terrain must be audited; no native teleport/reset is performed.'])
    def send(values):
        guard()
        pad.left_joystick_float(x_value_float=values['x'],y_value_float=values['y'])
        pad.right_trigger_float(value_float=values['r2']);pad.update()
    try:
        pad=vgamepad.VDS4Gamepad();pad.reset();pad.update()
        driver=Drive(target);driver.focus()
        rect=driver.rect()
        if rect is None:raise RuntimeError('Target window missing')
        if a.resume_menu:
            if a.target!='original':raise RuntimeError('Resume menu applies only to observed original pause')
            driver.click(rect[2]*.5,rect[3]*.288)
        if a.target=='preview':driver.key('0x52','tap',pause=0.)
        time.sleep(.8)
        sign=-1. if case['setup']=='face_left_rest' else 1.
        send(dict(x=sign,y=0.,r2=0.));time.sleep(.7)
        if a.require_opposite:
            geometry_reader=NativeState(proc['pid'],proc['base'])
            report['setup_held_geometry']=geometry_reader.turn_geometry()
        pad.reset();pad.update();time.sleep(1.2)
        shot(str(output/'before.png'),exe=target+'.exe',scale=.33)
        report['readiness']=wait_ready(a.target,proc,a.preview_trace,guard)
        if geometry_reader:
            initial=geometry_reader.turn_geometry()
            report['initial_turn_geometry']=initial
            held=report['setup_held_geometry']
            dot=sum(f*-d for f,d in zip(initial['forward'],held['direction']))
            report['setup_opposite_dot']=dot
            if (not initial['unchanged'] or not held['unchanged'] or held['norm']<.6
                or initial['actor_flags']&0x400000 or dot>=-.70710677):
                raise RuntimeError('Initial facing does not oppose observed setup direction; no case input sent')
        commands=[[sys.executable,str(ROOT/'tools/jade/probe_gamepad_input.py'),'--seconds',str(min(15,case['duration']+1.2))]]
        if a.target=='original':commands.insert(0,[sys.executable,str(ROOT/'tools/jade/capture_tracking_sequence.py'),
            '--pid',str(proc['pid']),'--base',str(proc['base']),'--samples','256','--interval-ms','25',
            '--start-delay','0','--max-seconds',str(min(8,case['duration']+.9))])
        for command in commands:children.append((command,subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)))
        time.sleep(.4)
        origin=time.perf_counter();report['input_origin_performance_counter']=origin
        report['input_origin_unix_ns']=time.time_ns()
        step=0
        first_direction_checked=False
        while True:
            elapsed=time.perf_counter()-origin
            values=evaluate(case['points'],elapsed)
            if geometry_reader and not first_direction_checked:
                geometry=geometry_reader.turn_geometry()
                if geometry['unchanged'] and geometry['norm']>0:
                    dot=sum(f*d for f,d in zip(initial['forward'],geometry['direction']))
                    report['first_input_geometry']=geometry|dict(dot_against_initial_forward=dot,t=elapsed)
                    first_direction_checked=True
                    if geometry['actor']!=initial['actor'] or geometry['actor_flags']&0x400000 or dot>=-.70710677:
                        raise RuntimeError('Delivered input no longer opposes initial facing; neutralizing')
            send(values)
            events.append(dict(elapsed=elapsed,performance_counter=time.perf_counter(),unix_ns=time.time_ns(),**values))
            if elapsed>=case['duration']:break
            step+=1
            # Deadline scheduling: retain real timestamps and lateness, never hide dropped updates.
            time.sleep(max(0,origin+step/100-time.perf_counter()))
        pad.reset();pad.update()
        if geometry_reader and not first_direction_checked:
            raise RuntimeError('No stable accepted direction for opposite geometry check')
        report['input_end_unix_ns']=time.time_ns()
        for command,child in children:
            out,err=child.communicate(timeout=20)
            result=dict(command=command,returncode=child.returncode,stdout=out,stderr=err)
            if child.returncode==0:
                result['parsed']=json.loads(out.strip().splitlines()[-1])
            results.append(result)
            if child.returncode:raise RuntimeError(err)
        if a.target=='preview':
            with a.preview_trace.open() as file:
                rows=[]
                for line in file:
                    try: row=json.loads(line)
                    except json.JSONDecodeError:continue
                    if report['input_origin_unix_ns']<=row['unix_ns']<=report['input_end_unix_ns']:rows.append(row)
            (output/'preview.json').write_text(json.dumps(rows)+'\n')
            report['preview_samples']=len(rows)
            if not rows:raise RuntimeError('No preview telemetry; restart REBGE with REBGE_MOVEMENT_TRACE')
        shot(str(output/'after.png'),exe=target+'.exe',scale=.33)
    except Exception as exc:
        error=repr(exc);raise
    finally:
        if pad is not None:pad.reset();pad.update()
        if geometry_reader is not None:geometry_reader.close()
        if driver is not None:driver.close()
        from return_chat_focus import return_chat_focus
        report['focus_return'] = return_chat_focus()
        for _,child in children:
            if child.poll() is None:child.terminate()
        report.update(events=events,collectors=results,error=error,status='recorded_unqualified' if error is None else 'failed')
        (output/'run.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(dict(report=str(output/'run.json'),status=report['status'])))

if __name__=='__main__':main()
