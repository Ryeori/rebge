"""Two bounded C+Tab chords with read-only telemetry and guaranteed key release."""
import argparse, ctypes, datetime, hashlib, json, struct, sys, time
from ctypes import wintypes
from pathlib import Path
from return_chat_focus import return_chat_focus

p=argparse.ArgumentParser()
p.add_argument('--pid',type=int,required=True)
p.add_argument('--base',type=lambda s:int(s,0),required=True)
a=p.parse_args()
sys.path.insert(0,'C:/Users/Dan/.codex/plugins/cache/universal-modder/universal-modder/0.2.0')
from um.win import Drive, shot
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
k.ReadProcessMemory.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
k.CloseHandle.argtypes=[wintypes.HANDLE]
h=k.OpenProcess(0x1010,False,a.pid)
if not h:raise ctypes.WinError(ctypes.get_last_error())
def read(addr,n):
    b=ctypes.create_string_buffer(n);got=ctypes.c_size_t()
    if not k.ReadProcessMemory(h,addr,b,n,ctypes.byref(got)) or got.value!=n:raise ctypes.WinError(ctypes.get_last_error())
    return b.raw
def rel(addr):return a.base+addr-0x140000000
def val(addr,fmt):return struct.unpack(fmt,read(addr,struct.calcsize(fmt)))[0]
def ptr(addr):return val(addr,'<Q')
outdir=Path('reports/ghidra/cheats-config/mode-cycle-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
outdir.mkdir(parents=True)
rows=[];events=[];driver=None
def sample(label):
    device=val(rel(0x1420a282c),'<i')
    row=dict(t=time.perf_counter(),label=label,device=device)
    for name,addr,fmt in [('gate',0x1419a0279,'<B'),('provider',0x142137a30,'<i'),('mask',0x1420a32e4,'<I'),('layout',0x14213760c,'<i'),('input_active',0x1420a32e0,'<i'),('time',0x1420a3310,'<f'),('dt',0x1420a3318,'<f'),('pause_offset',0x14210c174,'<f')]:
        row[name]=val(rel(addr),fmt)
    if 0<=device<4:
        row['current']=read(rel(0x1420a2e40)+device*0x128,29).hex()
        row['previous']=read(rel(0x1420a2980)+device*0x128,29).hex()
    row['raw_C_Tab']=read(rel(0x1420a2870)+0x2e,1).hex()+read(rel(0x1420a2870)+0xf,1).hex()
    row['remapper']=hex(ptr(rel(0x142138420))-a.base+0x140000000)
    row['bindings']=[val(rel(addr),'<H') for addr in (0x14195aac4,0x14195aae4)]
    q=ptr(rel(0x142160fd0))
    row['manager_mode_ptr']=hex(q)
    if q:row['manager']=[val(q-0x34,'<i'),val(q,'<i'),val(q+4,'<i')]
    q=ptr(rel(0x142141a68))
    if q:row['global_timescale']=val(q-0x74+0xde4,'<f')
    rows.append(row)
def observe(label,seconds):
    end=time.perf_counter()+seconds
    while time.perf_counter()<end:sample(label);time.sleep(.008)
def cmd(value):
    events.append(dict(t=time.perf_counter(),command=value,result=driver.cmd(value,retry=False)))
try:
    driver=Drive('bge');cmd('focus');cmd('scanmode on')
    observe('baseline',.3)
    if not rows[-1].get('manager')==[0,0,0]:raise RuntimeError('Expected normal manager command/mode/latch 0/0/0; no chord sent.')
    for index in (1,2):
        cmd('key 0x43 down');observe(f'C-held-{index}',.2)
        cmd('key 0x09 down');observe(f'chord-{index}',.22)
        cmd('key 0x09 up');observe(f'Tab-released-{index}',.2)
        cmd('key 0x43 up');observe(f'released-{index}',.5)
        events.append(dict(capture=shot(str(outdir/f'after-{index}.png'),exe='bge.exe',scale=.33)))
finally:
    if driver:
        for key in ('0x09','0x43'):
            try:cmd('key '+key+' up')
            except Exception as error:events.append(dict(cleanup_error=repr(error)))
        driver.close()
    k.CloseHandle(h)
    events.append(dict(focus_return=return_chat_focus()))
    (outdir/'trace.json').write_text(json.dumps(dict(parameters=vars(a),rows=rows,events=events,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),limits='Sequential reads, no game memory writes. Two chords only; no movement or save operations.'),indent=2))
    print(outdir)
    for label in dict.fromkeys(row['label'] for row in rows):
        selected=[r for r in rows if r['label']==label]
        print(label,'manager',sorted({tuple(r.get('manager',[])) for r in selected}),'raw',sorted({r['raw_C_Tab'] for r in selected}),'slots6/8',sorted({(bytes.fromhex(r['current'])[6],bytes.fromhex(r['current'])[8]) for r in selected if 'current' in r}),'mask',sorted({r['mask'] for r in selected}))
