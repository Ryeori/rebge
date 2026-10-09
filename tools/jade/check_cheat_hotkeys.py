"""Bounded authorized hotkey probe, read-only memory and foreground guarded input."""
import argparse, ctypes, datetime, json, struct, sys, time
from ctypes import wintypes
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True);p.add_argument('--base',type=lambda x:int(x,0),required=True);a=p.parse_args()
sys.path.insert(0,'C:/Users/Dan/.codex/plugins/cache/universal-modder/universal-modder/0.2.0')
from um.win import Drive
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
k.ReadProcessMemory.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
k.CloseHandle.argtypes=[wintypes.HANDLE]
h=k.OpenProcess(0x1010,False,a.pid)
if not h:raise ctypes.WinError(ctypes.get_last_error())
def read(addr,size):
    b=ctypes.create_string_buffer(size);n=ctypes.c_size_t()
    if not k.ReadProcessMemory(h,addr,b,size,ctypes.byref(n)) or n.value!=size:raise ctypes.WinError(ctypes.get_last_error())
    return b.raw
def rel(addr):return a.base+addr-0x140000000
def ptr(addr):return struct.unpack('<Q',read(addr,8))[0]
rows=[];events=[];d=Drive('bge')
def command(cmd):
    result=d.cmd(cmd,retry=False);events.append(dict(t=time.perf_counter(),command=cmd,result=result))
def sample(label):
    r=dict(t=time.perf_counter(),label=label,flag=read(rel(0x1419a0279),1).hex())
    for name,addr in [('current',0x142138788),('previous',0x142138780)]:
        q=ptr(rel(addr));r[name+'_pointer']=hex(q)
        r[name]={hex(i):read(q+i,1).hex() for i in (0x11,0x61,0x64,0xa2,0xa3)} if q else None
    q=ptr(rel(0x142141a68));r['global_brain']=hex(q-0x74) if q else None
    r['de4_bits']=read(q-0x74+0xde4,4).hex() if q else None
    r['de4']=struct.unpack('<f',bytes.fromhex(r['de4_bits']))[0] if q else None
    r['dt']=struct.unpack('<f',read(rel(0x1420a3318),4))[0]
    r['raw_scan']={hex(i):read(rel(0x1420a2870)+i,1).hex() for i in (0x1d,0x9d,0x4f,0x4b,0x3c)}
    rows.append(r)
def observe(label,seconds):
    end=time.perf_counter()+seconds
    while time.perf_counter()<end:sample(label);time.sleep(.01)
try:
    command('focus');observe('baseline',.2)
    for mode in ('off','on'):
        command('scanmode '+mode)
        for digit in ('0x61','0x64'):
            command('key 0x11 down');observe(mode+' ctrl',.12)
            command('key '+digit+' down');observe(mode+' '+digit,.35)
            command('key '+digit+' up');command('key 0x11 up');observe(mode+' released '+digit,.25)
finally:
    for vk in ('0x61','0x64','0x11'):
        try:command('key '+vk+' up')
        except Exception as exc:events.append(dict(cleanup_error=str(exc)))
    d.close();k.CloseHandle(h)
    path=Path('reports/ghidra/cheats-config/hotkey-probe-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
    path.write_text(json.dumps(dict(parameters=vars(a),rows=rows,events=events,limits='Sequential reads may miss key edges; no memory writes.'),indent=2))
    print(path)
    for label in sorted({r['label'] for r in rows}):
        selected=[r for r in rows if r['label']==label]
        print(label,'de4',sorted({r['de4'] for r in selected}), 'keys',list({json.dumps(r['current'],sort_keys=True) for r in selected}), 'raw_scan',list({json.dumps(r['raw_scan'],sort_keys=True) for r in selected}))
