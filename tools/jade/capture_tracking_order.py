"""Bounded readonly observation of tracking matrix publication order.

Snapshots are sequential reads, not atomic callback-entry captures. Only
changed observations are retained; no debug attachment or game input.
"""
import argparse
import ctypes
import datetime
import json
import struct
import time
from ctypes import wintypes
from pathlib import Path
from project_paths import report_path
from jade_runtime_tracks import prepare_clip_reads,capture_clip_link


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('snapshot',type=Path)
    args=parser.parse_args()
    previous=json.loads(args.snapshot.read_text())
    sample=previous['samples'][-1]
    base=int(previous['module_base'],16)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.ReadProcessMemory.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
    kernel.ReadProcessMemory.restype=wintypes.BOOL
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x1010,False,previous['pid'])
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    def read(address,size):
        if address<0x10000 or not 0<size<=4096:raise ValueError('Invalid bounded read')
        buffer=ctypes.create_string_buffer(size);count=ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle,address,buffer,size,ctypes.byref(count)) or count.value!=size:
            raise ctypes.WinError(ctypes.get_last_error())
        return buffer.raw
    def pointer(address):return struct.unpack('<Q',read(address,8))[0]
    def global_address(address):return base+address-0x140000000
    try:
        actor=int(sample['actor']['address'],16)
        if pointer(global_address(0x142157ec8))!=actor:raise ValueError('Actor changed; refresh full sequence')
        component=pointer(pointer(actor+0x20))
        instance=pointer(component+0x70)
        link=pointer(instance+8)
        link_prefix=read(link,16)
        resource,states=struct.unpack('<QQ',link_prefix)
        track_count=struct.unpack_from('<H',read(resource,16),8)[0]
        if not 0<track_count<=128:raise ValueError('Unexpected tracking clip count')
        prepared_clip=prepare_clip_reads(read,link)
        primary_clip=capture_clip_link(read,link,prepared_reads=prepared_clip,include_payloads=False)
        # Clip switches invalidate both the state address and the track count.
        # Keep immutable metadata per observed resource; each row names its clip.
        clip_catalog={hex(resource):primary_clip}
        initial_instance,initial_link,initial_resource=instance,link,resource
        initial_count,initial_clip=track_count,primary_clip
        brain=int(sample['brain_address'],16)
        target_storage=int(sample['target_storage_address'],16)
        addresses={'actor_world':pointer(actor+0x10)}
        for slot in (0,9,10,19,20):
            obj=int(sample['objects'][slot]['address'],16)
            linked=pointer(pointer(obj+0x20)+0x10)
            addresses[f'{slot}_world']=pointer(obj+0x10)
            addresses[f'{slot}_local']=linked+0x10
        rows=[];last=None;started=time.perf_counter();iterations=0
        while time.perf_counter()-started<3 and iterations<30000 and len(rows)<2048:
            tick=time.perf_counter()-started
            next_instance=pointer(component+0x70)
            next_link=pointer(next_instance+8)
            next_prefix=read(next_link,16)
            if (next_instance,next_link,next_prefix)!=(instance,link,link_prefix):
                instance,link,link_prefix=next_instance,next_link,next_prefix
                resource,states=struct.unpack('<QQ',link_prefix)
                track_count=struct.unpack_from('<H',read(resource,16),8)[0]
                if not 0<track_count<=128:raise ValueError('Unexpected switched clip count')
                if hex(resource) not in clip_catalog:
                    prepared_clip=prepare_clip_reads(read,link)
                    metadata=capture_clip_link(
                        read,link,prepared_reads=prepared_clip,include_payloads=False)
                    if metadata.get('resource_address')!=hex(resource) or read(link,16)!=link_prefix:
                        # Retry with freshly resolved pointers; never label mixed metadata.
                        link_prefix=b''
                        iterations+=1
                        continue
                    clip_catalog[hex(resource)]=metadata
            before=read(global_address(0x1419a1480),4)
            callback_before=read(global_address(0x14210c150),4)
            header=read(instance,0x5c)
            states_before=read(states,track_count*12)
            delta_raw=read(global_address(0x1420a3318),4)
            brain_raw=read(brain+0x604,28)
            target_raw=read(target_storage,8)
            component_flags=read(component,2)
            actor_flags=struct.unpack('<I',read(actor+4,4))[0]
            reference_address=(addresses['actor_world']+(0x88 if actor_flags&0x10000 else 0x44)
                               if actor_flags&0x4000000 else 0)
            reference_raw=read(reference_address,68) if reference_address else None
            height_raw=read(component+0xb4,4)
            sign_raw=read(global_address(0x1420b0b98),12)
            multiplier_raw=read(global_address(0x14173ccac),4)
            matrices={name:read(address,68).hex() for name,address in addresses.items()}
            prefix=read(component+0xaa,12).hex()
            descriptor=pointer(component+0x90)
            phase_index=bytes.fromhex(prefix)[2]
            phase_address=descriptor+phase_index*32+0x23
            phase_raw=(read(phase_address,3) if descriptor and phase_index<read(descriptor,1)[0] else None)
            clip_stable=(read(states,track_count*12)==states_before
                and read(instance,0x5c)==header and read(link,16)==link_prefix
                and pointer(component+0x70)==instance)
            after=read(global_address(0x1419a1480),4)
            callback_after=read(global_address(0x14210c150),4)
            actor_world_unchanged=read(addresses['actor_world'],68).hex()==matrices['actor_world']
            inputs_stable=(read(brain+0x604,28)==brain_raw
                and read(global_address(0x1420a3318),4)==delta_raw
                and read(target_storage,8)==target_raw
                and read(component,2)==component_flags
                and read(component+0xaa,12).hex()==prefix
                and pointer(component+0x90)==descriptor
                and (read(phase_address,3)==phase_raw if phase_raw else True)
                and (read(reference_address,68)==reference_raw if reference_raw else True)
                and read(component+0xb4,4)==height_raw
                and read(global_address(0x1420b0b98),12)==sign_raw
                and read(global_address(0x14173ccac),4)==multiplier_raw)
            key=(tuple(matrices.values()),prefix,before,after,states_before,header,clip_stable,
                 delta_raw,brain_raw,target_raw,inputs_stable,callback_before,callback_after,actor_world_unchanged)
            if key!=last:
                rows.append(dict(elapsed_seconds=tick,matrices=matrices,component_aa_b5_hex=prefix,
                    primary_resource_address=hex(resource),
                    callback3_marker_before=struct.unpack('<I',callback_before)[0],
                    callback3_marker_after=struct.unpack('<I',callback_after)[0],
                    actor_world_unchanged=actor_world_unchanged,
                    pass_before=struct.unpack('<I',before)[0],pass_after=struct.unpack('<I',after)[0],
                    primary_states_hex=states_before.hex(),primary_header_hex=header.hex(),
                    primary_clip_unchanged=clip_stable,
                    delta_time=struct.unpack('<f',delta_raw)[0],brain_604_61f_hex=brain_raw.hex(),
                    target_reference=hex(struct.unpack('<Q',target_raw)[0]),tracking_inputs_unchanged=inputs_stable,
                    component_flags_u16=struct.unpack('<H',component_flags)[0],actor_flags=hex(actor_flags),
                    actor_reference_matrix_hex=reference_raw.hex() if reference_raw else None,
                    component_height_b4=struct.unpack('<f',height_raw)[0],current_phase_index=phase_index,
                    current_phase_flags=phase_raw[0] if phase_raw else None,
                    current_phase_control=struct.unpack_from('<H',phase_raw,1)[0] if phase_raw else None,
                    sign_axis=list(struct.unpack('<3f',sign_raw)),strength_multiplier=struct.unpack('<f',multiplier_raw)[0],
                    read_window_ms=(time.perf_counter()-started-tick)*1000))
                last=key
            iterations+=1
        unchanged=(pointer(global_address(0x142157ec8))==actor and pointer(pointer(actor+0x20))==component)
        output=report_path('stage43-tracking-order-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
        result=dict(read_only=True,source_snapshot=str(args.snapshot),pid=previous['pid'],
            primary_instance_address=hex(initial_instance),primary_link_address=hex(initial_link),
            primary_resource_address=hex(initial_resource),primary_track_count=initial_count,
            primary_clip=initial_clip,clip_catalog=clip_catalog,
            addresses={name:hex(address) for name,address in addresses.items()},rows=rows,
            iterations=iterations,actor_component_unchanged=unchanged,
            limitations=['Sequential matrix reads may straddle writes; not atomic callback inputs.',
                        'Observe publication changes only; no causal parity or unique frame claim.'])
        output.write_text(json.dumps(result,indent=2))
        print(json.dumps(dict(report=str(output),observations=len(rows),iterations=iterations,
                             actor_component_unchanged=unchanged)))
    finally:kernel.CloseHandle(handle)


if __name__=='__main__':main()
