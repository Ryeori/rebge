"""Read-only XInput observation; never sends controller input or vibration."""
import argparse
import ctypes
import datetime
import json
import time
from pathlib import Path

class Gamepad(ctypes.Structure):
    _fields_=[('buttons',ctypes.c_uint16),('left_trigger',ctypes.c_uint8),('right_trigger',ctypes.c_uint8),
              ('left_x',ctypes.c_int16),('left_y',ctypes.c_int16),('right_x',ctypes.c_int16),('right_y',ctypes.c_int16)]
class State(ctypes.Structure):
    _fields_=[('packet',ctypes.c_uint32),('gamepad',Gamepad)]
class JoyInfo(ctypes.Structure):
    _fields_=[(name,ctypes.c_uint32) for name in ('size','flags','x','y','z','r','u','v','buttons','button_number','pov','reserved1','reserved2')]
parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=float,default=0.);args=parser.parse_args()
if not 0<=args.seconds<=15:parser.error('Bounded observation: 0..15 seconds')
library=None
for name in ('xinput1_4.dll','xinput1_3.dll','xinput9_1_0.dll'):
    try: library=ctypes.WinDLL(name);break
    except OSError:pass
if library is None:raise RuntimeError('No XInput library available')
get_state=library.XInputGetState;get_state.argtypes=[ctypes.c_uint32,ctypes.POINTER(State)];get_state.restype=ctypes.c_uint32
winmm=ctypes.WinDLL('winmm.dll'); joy_get=winmm.joyGetPosEx
joy_get.argtypes=[ctypes.c_uint32,ctypes.POINTER(JoyInfo)];joy_get.restype=ctypes.c_uint32
def legacy_states():
    result=[]
    for index in range(16):
        info=JoyInfo();info.size=ctypes.sizeof(info);info.flags=0xff
        status=int(joy_get(index,ctypes.byref(info)))
        if status==0:result.append(dict(index=index,**{name:int(getattr(info,name)) for name,_ in JoyInfo._fields_}))
    return result
rows=[];previous={};legacy_rows=[];previous_legacy=None;start=time.perf_counter()
while True:
    elapsed=time.perf_counter()-start
    for index in range(4):
        state=State();status=int(get_state(index,ctypes.byref(state)))
        value=dict(index=index,status=status)
        if status==0:value.update(packet=state.packet,**{name:int(getattr(state.gamepad,name)) for name,_ in Gamepad._fields_})
        if value!=previous.get(index):rows.append(dict(elapsed_seconds=elapsed,**value));previous[index]=value
    legacy=legacy_states()
    if legacy!=previous_legacy:legacy_rows.append(dict(elapsed_seconds=elapsed,devices=legacy));previous_legacy=legacy
    if elapsed>=args.seconds:break
    time.sleep(.01)
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
path=Path(f'reports/jade/gamepad-input-{stamp}.json')
path.write_text(json.dumps(dict(library=library._name,start_performance_counter=start,rows=rows,winmm_rows=legacy_rows,winmm_connected=legacy,limits=['Read-only XInput/WinMM values; physical stick input cannot be synthesized by these getters.','Wall-clock timestamps are not native callback times.']),indent=2)+'\n')
print(json.dumps(dict(report=str(path),devices=list(previous.values()),winmm_connected=legacy,changes=len(rows),winmm_changes=len(legacy_rows))))
