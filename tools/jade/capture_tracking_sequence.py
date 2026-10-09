"""Short readonly pose/state sequence; does not pause or drive the game."""
import argparse
import ctypes
import datetime
import json
import struct
import time
from ctypes import wintypes

from jade_runtime_tracks import prepare_clip_reads,capture_clip_link
from jade_tracking_target import variable_storage,resolve_actor_reference
from jade_clip_consistency import check_clip_prefix
from jade_modifier24 import capture_modifier24,check_modifier24_records
from jade_runtime_phase import transition_phase,capture_phase_descriptor
from project_paths import report_path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--base',type=lambda x:int(x,0),required=True)
    parser.add_argument('--samples',type=int,default=128)
    parser.add_argument('--start-delay',type=float,default=0)
    parser.add_argument('--interval-ms',type=float,default=2)
    parser.add_argument('--max-seconds',type=float,default=5.,help='Bounded recording window, 1..8 seconds')
    args=parser.parse_args()
    if not 2<=args.samples<=256:
        raise ValueError('Sequence limited to2..256 samples')
    if not 1.<=args.max_seconds<=8.:
        raise ValueError('Recording window limited to1..8 seconds')
    if not 0<=args.start_delay<=10 or not 0<=args.interval_ms<=50:
        raise ValueError('Delay limited to0..10s and interval to0..50ms')
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.ReadProcessMemory.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
    kernel.ReadProcessMemory.restype=wintypes.BOOL
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x1010,False,args.pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    def read(address,size):
        if address<0x10000 or not 0<size<=65536:
            raise ValueError('Bounded memory read required')
        buffer=ctypes.create_string_buffer(size);count=ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle,address,buffer,size,ctypes.byref(count)) or count.value!=size:
            raise ctypes.WinError(ctypes.get_last_error())
        return buffer.raw
    def pointer(address):return struct.unpack('<Q',read(address,8))[0]
    def global_address(address):return args.base+address-0x140000000
    matrix_reads={}
    def matrix(address):
        raw=read(address,68)
        matrix_reads[address]=raw
        values=struct.unpack('<16fI',raw)
        return list(values[:16]),values[16]
    def tracking_globals():
        blocked_count=struct.unpack('<i',read(global_address(0x1421015b8),4))[0]
        if blocked_count>512:raise ValueError('Unexpected blocked-target count')
        blocked=(list(struct.unpack('<'+'Q'*blocked_count,
            read(global_address(0x142101690),blocked_count*8))) if blocked_count>0 else [])
        return dict(sign_axis=list(struct.unpack('<3f',read(global_address(0x1420b0b98),12))),
            strength_multiplier=struct.unpack('<f',read(global_address(0x14173ccac),4))[0],
            blocked_targets=[hex(value) for value in blocked],
            limit_overrides={hex(address):struct.unpack('<f',read(global_address(address),4))[0]
                for address in (0x1421015ac,0x1421015b4,0x1421015a0,0x14210159c,
                                0x1421015a4,0x1421015b0,0x1421015a8)})
    time.sleep(args.start_delay)
    samples=[];started=time.perf_counter()
    try:
        for index in range(args.samples):
            if time.perf_counter()-started>args.max_seconds:
                break
            sample_started=time.perf_counter()
            matrix_reads.clear()
            update_pass_before=struct.unpack('<I',read(global_address(0x1419a1480),4))[0]
            actor=pointer(global_address(0x142157ec8))
            visual=pointer(actor+0x20);component=pointer(visual)
            state=read(component,0xbc)
            phase_descriptor_address=struct.unpack_from('<Q',state,0x90)[0]
            primary_phase_descriptor=capture_phase_descriptor(read,phase_descriptor_address)
            actor_dispatch_prefix=read(actor+4,0x30)
            entry_manager_gate=struct.unpack('<I',read(global_address(0x14193f708),4))[0]
            instance=struct.unpack_from('<Q',state,0x70)[0]
            primary_block=read(instance,0x5c)
            link=pointer(instance+8)
            cache=prepare_clip_reads(read,link)
            resource,states=struct.unpack('<QQ',cache[link,16])
            track_count=struct.unpack_from('<H',cache[resource,16],8)[0]
            if not track_count:
                raise ValueError('Primary clip has no captured tracks')
            states_before=cache[states,track_count*12]
            marker_before=states_before[:4].hex()
            transition_instance=struct.unpack_from('<Q',state,0x78)[0]
            transition_block=(read(transition_instance,0x5c) if transition_instance>=0x10000 else None)
            transition_link=(struct.unpack_from('<Q',transition_block,8)[0] if transition_block else 0)
            transition_cache=(prepare_clip_reads(read,transition_link) if transition_link>=0x10000 else None)
            action_table=struct.unpack_from('<Q',state,0x98)[0]
            transition_phase_before=(transition_phase(read,action_table,transition_block) if transition_block else None)
            actor_matrix,actor_matrix_flags=matrix(pointer(actor+0x10))
            actor_flags=struct.unpack('<I',read(actor+4,4))[0]
            dynamics=pointer(visual+8)
            dynamics_raw=read(dynamics,0x60) if dynamics else None
            orientation_state=(struct.unpack_from('<Q',dynamics_raw,0x48)[0]
                               if dynamics_raw else 0)
            orientation_raw=read(orientation_state,0x14) if orientation_state else None
            reference_address=(pointer(actor+0x10)+(0x88 if actor_flags&0x10000 else 0x44)
                               if actor_flags&0x4000000 else 0)
            reference_raw=read(reference_address,68) if reference_address else None
            indexed=pointer(component+0x10);listing=pointer(indexed)
            count=struct.unpack('<I',read(listing+0x14,4))[0]
            if not 0<count<=512:
                raise ValueError('Unexpected indexed object count')
            entries=read(pointer(listing+0x18),count*16)
            roles_pointer=struct.unpack_from('<Q',state,0x68)[0]
            role_tags=list(read(roles_pointer+4,count)) if roles_pointer else None
            objects=[];object_prefixes={}
            for slot in range(count):
                obj=struct.unpack_from('<Q',entries,slot*16)[0]
                prefix=read(obj+4,0x30);object_prefixes[obj]=prefix
                flags=struct.unpack_from('<I',prefix,0)[0]
                world,world_flags=matrix(pointer(obj+0x10))
                row=dict(slot=slot,address=hex(obj),flags=hex(flags),matrix=world,matrix_flags=world_flags,
                         update_flags_u32=struct.unpack_from('<I',prefix,4)[0],
                         visitation_byte_33=prefix[0x2f])
                obj_visual=pointer(obj+0x20)
                linked=pointer(obj_visual+0x10) if obj_visual else 0
                if linked:
                    local,local_flags=matrix(linked+0x10)
                    row.update(linked_parent_address=hex(pointer(linked+8)),
                               linked_local_matrix=local,linked_local_matrix_flags=local_flags)
                if slot in (27,28):row['modifier24_records']=capture_modifier24(read,obj)
                objects.append(row)
            states_after=read(states,track_count*12)
            marker_after=states_after[:4].hex()
            context_link=pointer(actor+0x28)
            context=pointer(context_link+8)
            brain=pointer(context+0x78)
            selector_prefix=read(brain,0x60)
            selector_state=read(brain+0x10c4,0x64)
            direction_raw=read(brain+0xa50,12)
            direction_gate_raw=read(brain+0x1dc,4)
            input_norm_pointer=pointer(global_address(0x142141a68))
            input_norm_raw=read(input_norm_pointer,4) if input_norm_pointer else None
            heading_norm_pointer_raw=None;heading_norm_raw=None;heading_norm_error=None
            heading_norm_pointer=0
            try:
                heading_norm_pointer_raw=read(global_address(0x142156a70),8)
                heading_norm_pointer=struct.unpack('<Q',heading_norm_pointer_raw)[0]
                if heading_norm_pointer>=0x10000:
                    heading_norm_raw=read(heading_norm_pointer,4)
                else:
                    heading_norm_error='Pointer absent or below bounded read threshold'
            except (OSError,ValueError) as error:
                heading_norm_error=str(error)
            # Global_glob_exec_joy140d01010 publishes direction+38/norm+74.
            # Sally_sa_exec_demi_tour1411daf10 consumes these and actor state.
            joy_base=input_norm_pointer-0x74 if input_norm_pointer else 0
            joy_turn_raw=read(joy_base+0x38,0x40) if joy_base else None
            joy_filter_raw=read(joy_base+0x14,12) if joy_base else None
            filtered_direction_raw=read(brain+0x1e4,12)
            # Sally_sa_exec_sight_banking14110d470, ordinary branch. Keep
            # these optional observations separate from pose qualification.
            heading_brain_raw={hex(offset):read(brain+offset,4)
                               for offset in (0x1dc,0x10d0,0x10e4,0x1198)}
            heading_dt_raw=read(global_address(0x1420a3318),4)
            heading_scale_raw={};heading_scale_errors={}
            for address,size in ((0x1419a0290,4),(0x1420c3430,4),
                                 (0x1420c3450,8),(0x14173cd70,4)):
                try:
                    heading_scale_raw[hex(address)]=read(global_address(address),size)
                except (OSError,ValueError) as error:
                    heading_scale_raw[hex(address)]=None
                    heading_scale_errors[hex(address)]=str(error)
            heading_scale_pointer=(struct.unpack('<Q',heading_scale_raw['0x1420c3450'])[0]
                                   if heading_scale_raw.get('0x1420c3450') is not None else 0)
            heading_scale_ushort=None;heading_scale_ushort_error=None
            if heading_scale_pointer>=0x10000:
                try:
                    heading_scale_ushort=read(heading_scale_pointer,2)
                except (OSError,ValueError) as error:
                    heading_scale_ushort_error=str(error)
            else:
                heading_scale_ushort_error='Pointer absent or below bounded read threshold'
            heading_velocity_raw=None;heading_velocity_error=None
            try:
                heading_velocity_raw=read(dynamics+0x10,0x1c) if dynamics else None
            except (OSError,ValueError) as error:
                heading_velocity_error=str(error)
            turn_actor_raw={hex(offset):read(brain+offset,4)
                            for offset in (0x2c,0x34,0x4c0,0xda8,0x10c4,0x10d4,0x119c)}
            stationary_raw={hex(offset):read(brain+offset,4) for offset in (0x7b8,0xdac)}
            stationary_globals={hex(address):read(global_address(address),4) for address in (0x1420a3310,0x14210c174)}
            selector_exception=pointer(global_address(0x142141a60))
            exception_link=(pointer(selector_exception+0x28) if selector_exception>=0x10000 else 0)
            exception_flags=(struct.unpack('<H',read(exception_link+0x50,2))[0] if exception_link else 0)
            raw=read(brain+0x604,28)
            vm=pointer(context+0x88)
            target_storage=variable_storage(read,struct.unpack_from('<I',raw,4)[0],vm)
            target_reference=pointer(target_storage)
            special=struct.unpack('<QQ',read(pointer(global_address(0x14193f710)),16))
            target_resolved=resolve_actor_reference(target_reference,special)
            descriptor=struct.unpack_from('<Q',state,0x90)[0]
            phase_index=state[0xac]
            phase_count=read(descriptor,1)[0] if descriptor else 0
            phase_flags=(read(descriptor+phase_index*32+0x23,1)[0]
                         if phase_index<phase_count else None)
            phase_control=(struct.unpack('<H',read(descriptor+phase_index*32+0x24,2))[0]
                           if phase_index<phase_count else None)
            heading_descriptor_address=(descriptor+phase_index*32+0x23
                                        if descriptor and phase_index<phase_count else 0)
            heading_descriptor_raw=None;heading_descriptor_error=None
            try:
                heading_descriptor_raw=(read(heading_descriptor_address,1)
                                        if heading_descriptor_address else None)
            except (OSError,ValueError) as error:
                heading_descriptor_error=str(error)
            tracking_inputs=tracking_globals()
            update_pass_after=struct.unpack('<I',read(global_address(0x1419a1480),4))[0]
            snapshot=dict(index=index,elapsed_seconds=sample_started-started,
                pose_read_window_ms=(time.perf_counter()-sample_started)*1000,
                actor=dict(address=hex(actor),flags=hex(struct.unpack('<I',read(actor+4,4))[0]),
                           world_matrix=actor_matrix+[actor_matrix_flags]),objects=objects,
                component_flags_u16=struct.unpack_from('<H',state)[0],
                delta_time=struct.unpack('<f',read(global_address(0x1420a3318),4))[0],
                brain_604_61f_hex=raw.hex(),primary_instance_address=hex(instance),
                actor_context_address=hex(context),brain_address=hex(brain),
                target_storage_address=hex(target_storage),target_reference=hex(target_reference),
                target_resolved_address=hex(target_resolved),current_phase_flags=phase_flags,current_phase_index=phase_index,
                current_phase_control=phase_control,tracking_role_tags=role_tags,
                tracking_counter_af=state[0xaf],tracking_gate_b2=state[0xb2],
                tracking_inputs=tracking_inputs,
                brain_unchanged=read(brain+0x604,28)==raw,
                target_reference_unchanged=pointer(target_storage)==target_reference,
                primary_marker_before=marker_before,primary_marker_after=marker_after,
                primary_marker_unchanged=marker_before==marker_after,
                primary_states_before_hex=states_before.hex(),
                primary_states_after_hex=states_after.hex(),
                primary_states_unchanged=states_before==states_after,
                primary_link_unchanged=pointer(instance+8)==link and read(link,16)==cache[link,16],
                primary_resource_unchanged=read(resource,16)==cache[resource,16],
                component_prefix_unchanged=read(component,0xbc)==state,
                update_pass_before=update_pass_before,update_pass_after=update_pass_after,
                update_pass_unchanged=update_pass_before==update_pass_after,
                primary_instance_unchanged=pointer(component+0x70)==instance,
                primary_clip=capture_clip_link(read,link,prepared_reads=cache,include_payloads=False))
            if transition_cache is not None:
                snapshot['transition_phase']=transition_phase_before
                snapshot['transition_phase_unchanged']=transition_phase(read,action_table,transition_block)==transition_phase_before
                snapshot['transition_clip']=capture_clip_link(read,transition_link,
                    prepared_reads=transition_cache,include_payloads=False)
                snapshot['transition_consistency']=check_clip_prefix(read,transition_link,transition_cache)
                snapshot['transition_consistency']['instance_header_unchanged']=read(transition_instance,0x5c)==transition_block
                snapshot['transition_consistency']['instance_pointer_unchanged']=pointer(component+0x78)==transition_instance
                snapshot['transition_header_hex']=transition_block.hex()
                snapshot['transition_instance_address']=hex(transition_instance)
            snapshot['primary_header_hex']=primary_block.hex()
            snapshot['primary_header_unchanged']=read(instance,0x5c)==primary_block
            snapshot['actor_reference_address']=hex(reference_address)
            snapshot['actor_reference_matrix_hex']=reference_raw.hex() if reference_raw else None
            snapshot['actor_reference_unchanged']=(read(reference_address,68)==reference_raw
                                                   if reference_raw else True)
            snapshot['component_height_b4']=struct.unpack_from('<f',state,0xb4)[0]
            # Already checked as part of component_prefix_unchanged; retain
            # action/phase/repeat and caller delta for controller epoch audits.
            snapshot['component_aa_b5_hex']=state[0xaa:0xb6].hex()
            snapshot['selector_inputs']=dict(prefix_hex=selector_prefix.hex(),state_10c4_hex=selector_state.hex(),
                selection_value_48=struct.unpack_from('<f',selector_prefix,0x48)[0],
                actions_04_30=list(struct.unpack_from('<12i',selector_prefix,4)),
                exception_actor=hex(selector_exception),exception_flags=exception_flags,
                primary_disabled=bool(primary_block[0]&0x80),blend_active=bool(state[1]&2),
                unchanged=read(brain,0x60)==selector_prefix and read(brain+0x10c4,0x64)==selector_state)
            snapshot['standing_turn_inputs']=dict(
                native_function='1411daf10',global_joy_base=hex(joy_base),
                direction_38_norm_74_hex=joy_turn_raw.hex() if joy_turn_raw else None,
                actor_fields_hex={key:value.hex() for key,value in turn_actor_raw.items()},
                unchanged=bool(joy_turn_raw is not None and read(joy_base+0x38,0x40)==joy_turn_raw
                    and all(read(brain+int(key,16),4)==value for key,value in turn_actor_raw.items())),
                limits='Sequential reads; actor forward and time globals have separate consistency checks. Native callback order not proven.')
            snapshot['native_orientation_inputs']=dict(
                dynamics_address=hex(dynamics),dynamics_header_hex=dynamics_raw.hex() if dynamics_raw else None,
                block_48_address=hex(orientation_state),block_48_hex=orientation_raw.hex() if orientation_raw else None,
                unchanged=bool(dynamics_raw is not None and pointer(visual+8)==dynamics
                    and read(dynamics,0x60)==dynamics_raw
                    and (orientation_raw is None or read(orientation_state,0x14)==orientation_raw)),
                limits='Block48 is enabled by native Sally init; role and consumer remain unproven. Sequential reads are not callback inputs.')
            snapshot['native_direction_filter_inputs']=dict(
                native_function='1560e4150',global_joy_base=hex(joy_base),brain_address=hex(brain),
                raw_direction_14_hex=joy_filter_raw.hex() if joy_filter_raw else None,
                filtered_direction_1e4_hex=filtered_direction_raw.hex(),
                unchanged=bool(joy_filter_raw is not None and read(joy_base+0x14,12)==joy_filter_raw
                    and read(brain+0x1e4,12)==filtered_direction_raw),
                limits='Sequential stable reads. Sight_banking14110d470 consumes brain1E4; active branch and callback chronology are not established by these reads.')
            heading_velocity_unchanged=False;heading_velocity_reread_error=None
            heading_pointer_identity_unchanged=False;heading_pointer_identity_error=None
            try:
                heading_pointer_identity_unchanged=(pointer(actor+0x20)==visual
                    and pointer(visual+8)==dynamics
                    and pointer(actor+0x28)==context_link
                    and pointer(context_link+8)==context
                    and pointer(context+0x78)==brain)
            except (OSError,ValueError) as error:
                heading_pointer_identity_error=str(error)
            if heading_velocity_raw is not None:
                try:
                    heading_velocity_unchanged=(pointer(actor+0x20)==visual
                        and pointer(visual+8)==dynamics
                        and read(dynamics+0x10,0x1c)==heading_velocity_raw)
                except (OSError,ValueError) as error:
                    heading_velocity_reread_error=str(error)
            heading_descriptor_unchanged=False;heading_descriptor_reread_error=None
            if heading_descriptor_raw is not None:
                try:
                    heading_descriptor_unchanged=(pointer(component+0x90)==descriptor
                        and read(component+0xac,1)==bytes([phase_index])
                        and read(heading_descriptor_address,1)==heading_descriptor_raw)
                except (OSError,ValueError) as error:
                    heading_descriptor_reread_error=str(error)
            heading_norm_pointer_unchanged=False;heading_norm_unchanged=False
            heading_norm_identity_unchanged=False;heading_norm_reread_error=None
            try:
                heading_norm_pointer_unchanged=(heading_norm_pointer_raw is not None
                    and read(global_address(0x142156a70),8)==heading_norm_pointer_raw)
                heading_norm_unchanged=(heading_norm_raw is not None
                    and heading_norm_pointer_unchanged
                    and read(heading_norm_pointer,4)==heading_norm_raw)
                heading_norm_identity_unchanged=(heading_norm_pointer==input_norm_pointer
                    and heading_norm_pointer_unchanged
                    and pointer(global_address(0x142141a68))==input_norm_pointer)
            except (OSError,ValueError) as error:
                heading_norm_reread_error=str(error)
            snapshot['native_heading_norm_inputs']=dict(
                native_function='14110d470',resource_key='710047BC',brain_offset='0x74',
                pointer_global_address=hex(global_address(0x142156a70)),
                pointer_global_hex=heading_norm_pointer_raw.hex() if heading_norm_pointer_raw is not None else None,
                norm_address=hex(heading_norm_pointer),
                norm_hex=heading_norm_raw.hex() if heading_norm_raw is not None else None,
                norm_present=heading_norm_raw is not None,norm_error=heading_norm_error,
                pointer_unchanged=heading_norm_pointer_unchanged,norm_unchanged=heading_norm_unchanged,
                selector_norm_address=hex(input_norm_pointer),
                equals_selector_norm_pointer=heading_norm_pointer==input_norm_pointer,
                pointer_identity_unchanged=heading_norm_identity_unchanged,
                reread_error=heading_norm_reread_error,
                limits='Static sight_banking and animselector resolve resource710047BC context brain+74 separately. Recorded pointer equality confirms shared scalar only for these sequential observations; callback input identity/order is not atomic. This scalar is neither actor48 nor filtered1E4 length.')
            heading_scale_checks={};heading_scale_reread_errors={}
            for address,value in heading_scale_raw.items():
                heading_scale_checks[address]=False
                if value is not None:
                    try:
                        heading_scale_checks[address]=(read(global_address(int(address,16)),len(value))==value)
                    except (OSError,ValueError) as error:
                        heading_scale_reread_errors[address]=str(error)
            heading_scale_ushort_unchanged=False;heading_scale_ushort_reread_error=None
            if heading_scale_ushort is not None:
                try:
                    heading_scale_ushort_unchanged=(pointer(global_address(0x1420c3450))==heading_scale_pointer
                        and read(heading_scale_pointer,2)==heading_scale_ushort)
                except (OSError,ValueError) as error:
                    heading_scale_ushort_reread_error=str(error)
            snapshot['native_heading_time_scale_inputs']=dict(
                native_function='140b33710',
                globals_hex={key:value.hex() if value is not None else None
                             for key,value in heading_scale_raw.items()},
                globals_errors=heading_scale_errors,globals_unchanged=heading_scale_checks,
                globals_reread_errors=heading_scale_reread_errors,
                flag_1419a0290=(struct.unpack('<I',heading_scale_raw['0x1419a0290'])[0]
                                if heading_scale_raw.get('0x1419a0290') is not None else None),
                source_1420c3450_address=hex(heading_scale_pointer),
                source_ushort_hex=heading_scale_ushort.hex() if heading_scale_ushort is not None else None,
                source_ushort_present=heading_scale_ushort is not None,
                source_ushort_error=heading_scale_ushort_error,
                source_ushort_unchanged=heading_scale_ushort_unchanged,
                source_ushort_reread_error=heading_scale_ushort_reread_error,
                limits='Only yaw!=0 and flag1419A0290!=0 apply f32(1420C3430 / f32(float(source_u16)/constant14173CD70)) to yaw. Flag is transient animation-manager context; stable reads do not prove its value during the heading callback. Separate checks do not qualify the pose.')
            snapshot['native_heading_inputs']=dict(
                native_function='14110d470',brain_address=hex(brain),
                actor_address=hex(actor),visual_address=hex(visual),
                context_link_address=hex(context_link),context_address=hex(context),
                pointer_identity_unchanged=heading_pointer_identity_unchanged,
                pointer_identity_error=heading_pointer_identity_error,
                brain_fields_hex={key:value.hex() for key,value in heading_brain_raw.items()},
                brain_fields_unchanged=all(read(brain+int(key,16),4)==value
                                          for key,value in heading_brain_raw.items()),
                dt_1420a3318_hex=heading_dt_raw.hex(),
                dt_unchanged=read(global_address(0x1420a3318),4)==heading_dt_raw,
                runtime_module_address=hex(dynamics),
                runtime_velocity_10_2b_hex=(heading_velocity_raw.hex()
                                           if heading_velocity_raw is not None else None),
                runtime_velocity_present=heading_velocity_raw is not None,
                runtime_velocity_error=heading_velocity_error,
                runtime_velocity_unchanged=heading_velocity_unchanged,
                runtime_velocity_reread_error=heading_velocity_reread_error,
                descriptor_address=hex(descriptor),phase_index=phase_index,
                descriptor_byte_23_address=hex(heading_descriptor_address),
                descriptor_byte_23_hex=(heading_descriptor_raw.hex()
                                        if heading_descriptor_raw is not None else None),
                descriptor_byte_23_present=heading_descriptor_raw is not None,
                descriptor_byte_23_error=heading_descriptor_error,
                descriptor_byte_23_unchanged=heading_descriptor_unchanged,
                descriptor_byte_23_reread_error=heading_descriptor_reread_error,
                limits='Sequential observations, not atomic callback inputs. Runtime module +10/+14 components are multiplied by +28 scalar; raw bytes preserve all three. Descriptor byte uses current phase index AC. Separate rereads do not qualify pose or establish caller order.')
            snapshot['stationary_selector_inputs']=dict(
                mode_34=struct.unpack_from('<i',selector_prefix,0x34)[0],
                pending_44=struct.unpack_from('<i',selector_prefix,0x44)[0],
                last_action_10c4=struct.unpack_from('<i',selector_state,0)[0],
                selected_action_1124=struct.unpack_from('<i',selector_state,0x60)[0],
                brain_hex={key:value.hex() for key,value in stationary_raw.items()},
                globals_hex={key:value.hex() for key,value in stationary_globals.items()},
                unchanged=all(read(brain+int(key,16),4)==value for key,value in stationary_raw.items()) and
                    all(read(global_address(int(key,16)),4)==value for key,value in stationary_globals.items()),
                limitations='Sequential reads; timestamps are not atomic callback inputs.')
            snapshot['speed_writer_inputs']=dict(direction_hex=direction_raw.hex(),
                gate_1dc=struct.unpack('<i',direction_gate_raw)[0],
                input_norm_address=hex(input_norm_pointer),input_norm_hex=input_norm_raw.hex() if input_norm_raw else None,
                state_10c4_hex=selector_state.hex(),
                unchanged=read(brain+0xa50,12)==direction_raw and read(brain+0x1dc,4)==direction_gate_raw and
                    (input_norm_raw is None or read(input_norm_pointer,4)==input_norm_raw) and
                    read(brain+0x10c4,0x64)==selector_state,
                limitations='Sequential actor matrix, selector state and speed header; callback order not atomic.')
            # 1409ad760 selects A8; AA/A0 retain a queued target/transition record.
            # Raw bytes and a second read keep sequential-read stability explicit.
            snapshot['action_selection_90_bb_hex']=state[0x90:0xbc].hex()
            snapshot['current_action_index_a8']=struct.unpack_from('<H',state,0xa8)[0]
            snapshot['requested_action_index_aa']=struct.unpack_from('<H',state,0xaa)[0]
            snapshot['pending_transition_address_a0']=hex(struct.unpack_from('<Q',state,0xa0)[0])
            snapshot['deferred_action_speed_ae']=state[0xae]
            snapshot['action_selection_unchanged']=read(component+0x90,0x2c)==state[0x90:0xbc]
            snapshot['component_delta_b8']=struct.unpack_from('<f',state,0xb8)[0]
            snapshot['primary_speed_byte']=primary_block[2]
            snapshot['primary_phase_descriptor']=primary_phase_descriptor
            snapshot['primary_phase_descriptor_unchanged']=(
                capture_phase_descriptor(read,phase_descriptor_address)==primary_phase_descriptor)
            snapshot['actor_dispatch_prefix_hex']=actor_dispatch_prefix.hex()
            snapshot['actor_dispatch_prefix_unchanged']=read(actor+4,0x30)==actor_dispatch_prefix
            snapshot['reference_entry_gate_u32']=entry_manager_gate
            snapshot['reference_entry_manager_unchanged']=(
                struct.unpack('<I',read(global_address(0x14193f708),4))[0]==entry_manager_gate)
            snapshot['tracking_inputs_unchanged']=tracking_globals()==tracking_inputs
            snapshot['tracking_roles_unchanged']=(list(read(roles_pointer+4,count))==role_tags
                                                   if roles_pointer else True)
            snapshot['object_prefixes_unchanged']=all(read(address+4,0x30)==prefix
                for address,prefix in object_prefixes.items())
            snapshot['modifier24_states_unchanged']=check_modifier24_records(read,
                [record for obj in objects for record in obj.get('modifier24_records',[])])
            # A late-incremented pass counter alone misses writes inside a pass.
            # Recheck the exact 68-byte actor/world/local matrices we consumed.
            snapshot['pose_matrix_addresses_changed']=[hex(address)
                for address,raw in matrix_reads.items() if read(address,68)!=raw]
            snapshot['pose_matrices_unchanged']=not snapshot['pose_matrix_addresses_changed']
            snapshot['pose_matrix_count']=len(matrix_reads)
            # End marker must follow all checks and header reads.
            snapshot['update_pass_after']=struct.unpack('<I',read(global_address(0x1419a1480),4))[0]
            snapshot['update_pass_unchanged']=snapshot['update_pass_after']==update_pass_before
            snapshot['pose_read_window_ms']=(time.perf_counter()-sample_started)*1000
            samples.append(snapshot)
            time.sleep(args.interval_ms/1000)
        result=dict(schema='jade-tracking-sequence-v1',pid=args.pid,module_base=hex(args.base),
            start_performance_counter=started,
            recording_parameters=dict(samples=args.samples,interval_ms=args.interval_ms,max_seconds=args.max_seconds),
            utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),read_only=True,samples=samples,
            limits=['Marker equality is a consistency check, not an atomic frame guarantee.',
                    'Samples may repeat or skip game frames; no native input or memory writes.',
                    'Primary/retained transition states, target/current phase and blocked table observed; no atomic callback trace.',
                    'Update-pass counter is not proven a unique gameplay or rendered frame.'])
        output=report_path('stage43-tracking-sequence-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
        output.write_text(json.dumps(result,indent=2,allow_nan=False))
        print(json.dumps(dict(report=str(output),sample_count=len(samples),
            stable_markers=sum(s['primary_marker_unchanged'] for s in samples))))
    finally:
        kernel.CloseHandle(handle)


if __name__=='__main__':main()
