"""Read-only readiness: stable waiting123 without active incoming blend."""
import ctypes
import json
import struct
import time
from pathlib import Path

def preview_state(path):
    with Path(path).open('rb') as file:
        file.seek(0,2);end=file.tell();file.seek(max(0,end-16384))
        lines=file.read().splitlines()
    for line in reversed(lines):
        try:row=json.loads(line)
        except (json.JSONDecodeError,UnicodeDecodeError):continue
        return dict(action=123 if row['phase']=='WaitingIdle' else None,
            blend=bool((row.get('blend') or {}).get('active')),
            fresh=(time.time_ns()-row['unix_ns'])/1e9<.25,
            epoch=row['frame'],input_norm=row['input_strength'])
    return None

class NativeState:
    def __init__(self,pid,base):
        from ctypes import wintypes
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        self.kernel.OpenProcess.restype=wintypes.HANDLE
        self.kernel.ReadProcessMemory.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
        self.kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        self.handle=self.kernel.OpenProcess(0x1010,False,pid)
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
        self.base=base
    def read(self,address,size):
        buf=ctypes.create_string_buffer(size);count=ctypes.c_size_t()
        if not self.kernel.ReadProcessMemory(self.handle,address,buf,size,ctypes.byref(count)) or count.value!=size:
            raise ctypes.WinError(ctypes.get_last_error())
        return buf.raw
    def ptr(self,address):return struct.unpack('<Q',self.read(address,8))[0]
    def state(self):
        actor=self.ptr(self.base+0x2157ec8)
        component=self.ptr(self.ptr(actor+0x20))
        before=self.read(component,0xbc)
        normptr=self.ptr(self.base+0x2141a68)
        norm=struct.unpack('<f',self.read(normptr,4))[0] if normptr else None
        after=self.read(component,0xbc)
        return dict(action=struct.unpack_from('<H',before,0xa8)[0],blend=bool(before[1]&2),
            fresh=before==after,epoch=time.perf_counter(),input_norm=norm,
            limitation='Sequential bounded reads; stable prefix does not prove atomic callback inputs')
    def close(self):self.kernel.CloseHandle(self.handle)

    def turn_geometry(self):
        actor=self.ptr(self.base+0x2157ec8)
        matrixptr=self.ptr(actor+0x10)
        flags=self.read(actor+4,4)
        matrixraw=self.read(matrixptr,68)
        normptr=self.ptr(self.base+0x2141a68)
        joyraw=self.read(normptr-0x3c,0x40)
        values=struct.unpack('<16fI',matrixraw)
        return dict(actor=hex(actor),forward=[-values[i] for i in (4,5,6)],
                    actor_flags=struct.unpack('<I',flags)[0],
                    direction=list(struct.unpack_from('<3f',joyraw)),
                    norm=struct.unpack_from('<f',joyraw,0x3c)[0],
                    unchanged=self.read(actor+4,4)==flags and self.read(matrixptr,68)==matrixraw
                    and self.read(normptr-0x3c,0x40)==joyraw)

def wait_ready(target,proc,preview_trace,guard,timeout=5.):
    reader=NativeState(proc['pid'],proc['base']) if target=='original' else None
    observations=[];start=time.perf_counter();stable=None;last_epoch=None
    try:
        while time.perf_counter()-start<timeout:
            guard()
            state=reader.state() if reader else preview_state(preview_trace)
            observations.append(dict(t=time.perf_counter()-start,state=state))
            valid=state and state['action']==123 and not state['blend'] and state['fresh']
            valid=valid and state['input_norm'] is not None and abs(state['input_norm'])<.01
            if valid:
                if stable is None:stable=time.perf_counter()
                if state['epoch']!=last_epoch and time.perf_counter()-stable>=.15:
                    return observations
            else:stable=None
            if state:last_epoch=state['epoch']
            time.sleep(.025)
        raise RuntimeError('No stable neutral waiting123 within5s; inspect scene before another input')
    finally:
        if reader:reader.close()
