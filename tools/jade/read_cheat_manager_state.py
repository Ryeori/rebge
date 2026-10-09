"""Read-only snapshot of debug input bindings and Cheat_Manager runtime state."""
import argparse, ctypes, datetime, json, struct
from ctypes import wintypes
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--pid', type=int, required=True)
p.add_argument('--base', type=lambda x: int(x, 0), required=True)
a = p.parse_args()
k = ctypes.WinDLL('kernel32', use_last_error=True)
k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k.OpenProcess.restype = wintypes.HANDLE
k.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k.CloseHandle.argtypes = [wintypes.HANDLE]
h = k.OpenProcess(0x1010, False, a.pid)
if not h: raise ctypes.WinError(ctypes.get_last_error())
def read(addr, size):
    b = ctypes.create_string_buffer(size); n = ctypes.c_size_t()
    if not k.ReadProcessMemory(h, addr, b, size, ctypes.byref(n)) or n.value != size:
        raise ctypes.WinError(ctypes.get_last_error())
    return b.raw
def rel(addr): return a.base + addr - 0x140000000
def ptr(addr): return struct.unpack('<Q', read(addr, 8))[0]
out = dict(parameters=vars(a), limits='Sequential read-only snapshot; not callback observation.')
try:
    for name, addr, fmt in [('gate',0x1419a0279,'<B'), ('device',0x1420a282c,'<i'), ('provider',0x142137a30,'<i'), ('layout',0x14213760c,'<i'), ('input_mask',0x1420a32e4,'<I')]:
        out[name] = struct.unpack(fmt, read(rel(addr), struct.calcsize(fmt)))[0]
    out['remapper'] = hex(ptr(rel(0x142138420)) - a.base + 0x140000000)
    out['keyboard_scan_bindings'] = {str(slot): list(struct.unpack('<HH',read(rel(addr),4))) for slot,addr in [(6,0x14195aac4),(7,0x14195aacc),(8,0x14195aae4),(15,0x14195aad8)]}
    out['current_buttons'] = read(rel(0x1420a2e40) + max(0,out['device'])*0x128,29).hex()
    ctx = ptr(rel(0x1420c3490))
    out['callback_context'] = hex(ctx)
    if ctx:
        brain = ptr(ctx+0x78)
        out['callback_brain'] = hex(brain)
        if brain: out['callback_brain_first16_i32'] = list(struct.unpack('<16i',read(brain,64)))
    out['manager_initialized_pointers'] = {hex(addr):hex(ptr(rel(addr))) for addr in (0x142160f70,0x142161008,0x142160fd0,0x142160fe8)}
    mode_ptr = ptr(rel(0x142160fd0))
    if mode_ptr:
        out['manager_brain_from_actor7100e3af'] = hex(mode_ptr-0x34)
        out['manager_command_mode_latch'] = {name:struct.unpack('<i',read(mode_ptr-0x34+offset,4))[0] for name,offset in [('command',0),('mode',0x34),('pause_latch',0x38)]}
    out['pause_clock_offset'] = struct.unpack('<f',read(rel(0x14210c174),4))[0]
finally:
    k.CloseHandle(h)
path = Path('reports/ghidra/cheats-config/manager-state-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
path.write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
