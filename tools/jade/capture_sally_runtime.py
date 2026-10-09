"""Read-only, bounded snapshots of known native Sally pointers. No memory writes."""
import argparse,ctypes,json,struct,datetime,time
from ctypes import wintypes
from project_paths import report_path
from jade_runtime_tracks import capture_clip_link,prepare_clip_reads
from jade_actor_script_context import capture_actor_script_context
from jade_tracking_target import variable_storage,resolve_actor_reference,direct_target_position
from jade_clip_consistency import check_clip_prefix
from jade_modifier24 import capture_modifier24,check_modifier24_records

def main():
 p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True);p.add_argument('--base',type=lambda x:int(x,0),required=True);args=p.parse_args()
 kernel=ctypes.WinDLL('kernel32',use_last_error=True)
 kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
 kernel.ReadProcessMemory.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];kernel.ReadProcessMemory.restype=wintypes.BOOL
 kernel.CloseHandle.argtypes=[wintypes.HANDLE]
 handle=kernel.OpenProcess(0x1010,False,args.pid)
 if not handle:raise ctypes.WinError(ctypes.get_last_error())
 def read(address,size):
  if not 0<size<=65536:raise ValueError('Bounded read size')
  data=ctypes.create_string_buffer(size);n=ctypes.c_size_t()
  if not kernel.ReadProcessMemory(handle,address,data,size,ctypes.byref(n)) or n.value!=size:raise ctypes.WinError(ctypes.get_last_error())
  return data.raw
 def u64(a):return struct.unpack('<Q',read(a,8))[0]
 def u32(a):return struct.unpack('<I',read(a,4))[0]
 def relocated(a):return args.base+a-0x140000000
 result={'schema':'jade-sally-runtime-v1','pid':args.pid,'module_base':hex(args.base),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'read_only':True,'globals':{},'limits':['Unsynchronised snapshot; not a paused native frame. No inferred replacement for absent actor.']}
 try:
  for name,a in [('sally_callback',0x142157ec8),('default_actor',0x1420d6620)]:
   ptr=u64(relocated(a));result['globals'][name]=hex(ptr)
  # Global/callback inputs are observations, never attributed to Sally unless
  # the default actor matches her. Context may change between these reads.
  tracking={'yaw_sign_axis':struct.unpack('<3f',read(relocated(0x1420b0b98),12)),
            'delta_time':struct.unpack('<f',read(relocated(0x1420a3318),4))[0],
            'strength_multiplier':struct.unpack('<f',read(relocated(0x14173ccac),4))[0],
            'override_values':{f'{a:x}':struct.unpack('<f',read(relocated(a),4))[0]
                               for a in (0x1421015ac,0x1421015b4,0x1421015a0,
                                         0x14210159c,0x1421015a4,0x1421015b0,
                                         0x1421015a8)}}
  result['tracking_callback_inputs']=tracking
  blocked_count=struct.unpack('<i',read(relocated(0x1421015b8),4))[0]
  tracking['blocked_target_count']=blocked_count
  if blocked_count>512:
   tracking['blocked_targets_error']='Count exceeds bounded capture limit512'
  else:
   tracking['blocked_targets']=[hex(v) for v in struct.unpack(
      '<'+'Q'*max(0,blocked_count),read(relocated(0x142101690),blocked_count*8))] if blocked_count>0 else []
  active_context=u64(relocated(0x1420c3490))
  tracking['active_context_address']=hex(active_context)
  if active_context>=0x10000:
   try:
    brain=u64(active_context+0x78);vm_context=u64(active_context+0x88)
    tracking.update(brain_address=hex(brain),vm_context_address=hex(vm_context))
    if brain>=0x10000:
     brain_data=read(brain+0x604,28)
     tracking.update(brain_raw_604_61f_hex=brain_data.hex(),
                     base_word_604=struct.unpack_from('<I',brain_data,0)[0],
                     target_handle_608=struct.unpack_from('<I',brain_data,4)[0],
                     target_offset_60c=struct.unpack_from('<3f',brain_data,8),
                     tracking_word_618=struct.unpack_from('<I',brain_data,20)[0],
                     strength_61c=struct.unpack_from('<f',brain_data,24)[0])
   except OSError as error:
    tracking['context_read_error']=str(error)
  actor=int(result['globals']['sally_callback'],16)
  if actor<0x10000:
   def lookup(key,table):
    storage=u64(table);count=u32(table+8)
    if count>1000000:raise ValueError('Unexpected native lookup count')
    low,high=0,count
    while low<high:
     mid=(low+high)//2;k,v=struct.unpack('<QQ',read(storage+mid*16,16))
     if k<key:low=mid+1
     elif k>key:high=mid
     else:return v
    return 0xffffffffffffffff
   key=0x71003f5a
   if u32(relocated(0x14209fd44))==0:
    mapped=lookup(key,relocated(0x1420a0e08))
    if mapped!=0xffffffffffffffff:key=mapped&0xffffffff
   bucket=((key>>8)+key)&255
   ptr=lookup(key,relocated(0x1420a0ea0)+bucket*24)
   result['key_lookup']={'source_key':'71003F5A','mapped_key':hex(key),'bucket':bucket,'pointer':hex(ptr)}
   if ptr!=0xffffffffffffffff:actor=ptr
  if actor<0x10000:result['status']='Sally callback pointer not initialised'
  else:
   tracking['default_actor_matches_sally']=(int(result['globals']['default_actor'],16)==actor)
   try:
    result['actor_script_context']=capture_actor_script_context(read,actor)
    owned=result['actor_script_context']
    owned_brain=owned.get('tracking_brain')
    if owned_brain and int(owned['vm_context_address'],16)>=0x10000:
     target={};owned['tracking_target_observation']=target
     try:
      storage=variable_storage(read,owned_brain['target_handle_608'],
                               int(owned['vm_context_address'],16))
      value=u64(storage)
      special_table=u64(relocated(0x14193f710))
      special=struct.unpack('<QQ',read(special_table,16))
      resolved=resolve_actor_reference(value,special)
      target.update(storage_address=hex(storage),raw_reference=hex(value),
                    resolved_actor_address=hex(resolved),
                    position=direct_target_position(read,resolved))
     except (OSError,ValueError,NotImplementedError) as error:
      target['error']=str(error)
   except (OSError,ValueError) as error:
    result['actor_script_context']={'status':'capture_failed','error':str(error)}
   pose_started=time.perf_counter()
   update_pass_before=u32(relocated(0x1419a1480))
   flags=u32(actor+4);result['actor']={'address':hex(actor),'flags':hex(flags),'world_matrix':struct.unpack('<16fI',read(u64(actor+0x10),68))}
   visual=u64(actor+0x20);palette=u64(visual+0x18);count=u32(palette);storage=u64(palette+8)
   if count>512:raise ValueError('Unexpected palette count')
   result['palette']={'address':hex(storage),'count':count,'indirect':bool(flags&0x1000000)}
   if flags&0x1000000:raise ValueError('Expected direct actor palette, got references')
   data=read(storage,count*68);result['palette']['matrices']=[{'slot':i,'matrix':struct.unpack_from('<16f',data,i*68),'flags':struct.unpack_from('<I',data,i*68+64)[0]} for i in range(count)]
   component=u64(visual);indexed=u64(component+0x10);lst=u64(indexed);n=u32(lst+0x14)
   # Offsets read by native 1409bd3b0 and 1409bcd20. Keep unknown fields raw.
   state=read(component,0xbc)
   result['animation_state']={
    'component_address':hex(component),
    'component_flags_u16':struct.unpack_from('<H',state,0)[0],
    'action_index':struct.unpack_from('<H',state,0xaa)[0],
    'phase_index':state[0xac],'phase_repeat_counter':state[0xad],
    'deferred_switch_byte':state[0xae],
    'tracking_counter_byte_af':state[0xaf],
    'tracking_gate_byte_b2':state[0xb2],
    'deferred_delta_f32':struct.unpack_from('<f',state,0xb8)[0],
    'action_descriptor_address':hex(struct.unpack_from('<Q',state,0x90)[0]),
    'evidence':['1409bd3b0','1409bcd20'],'instances':{}}
   descriptor=struct.unpack_from('<Q',state,0x90)[0]
   if descriptor>=0x10000:
    phase_count=read(descriptor,1)[0]
    phase_data=read(descriptor,phase_count*32+8)
    result['animation_state']['current_action_phases']={
     'count':phase_count,'raw_hex':phase_data.hex(),
     'phases':[{'index':i,'flags_byte_23':phase_data[i*32+0x23],
                'control_word_24':struct.unpack_from('<H',phase_data,i*32+0x24)[0]}
               for i in range(phase_count)]}
   prepared_clips={}
   for name,offset in [('primary',0x70),('transition',0x78)]:
    instance=struct.unpack_from('<Q',state,offset)[0]
    entry={'address':hex(instance)}
    if instance>=0x10000:
     block=read(instance,0x5c)
     entry.update(flags_u16=struct.unpack_from('<H',block)[0],speed_byte=block[2],
                  clip_link_address=hex(struct.unpack_from('<Q',block,8)[0]),
                  raw_header_hex=block.hex())
     prepared_clips[name]=prepare_clip_reads(read,struct.unpack_from('<Q',block,8)[0])
     if name=='transition':
      entry.update(transition_flags=block[0x58],duration_byte=block[0x59],
                   elapsed_u16=struct.unpack_from('<H',block,0x5a)[0])
    result['animation_state']['instances'][name]=entry
   if n>512:raise ValueError('Unexpected indexed actor count')
   role_table=u64(component+0x68)
   result['tracking_role_tags']=(list(read(role_table+4,n)) if role_table else list(range(n)))
   result['tracking_role_table_address']=hex(role_table)
   result['selected_variants']=list(read(component+0x28,n))
   entries=read(u64(lst+0x18),n*16);objects=[];pending_geometry=[]
   for i in range(n):
    obj=struct.unpack_from('<Q',entries,i*16)[0]
    if obj<0x10000:objects.append({'slot':i,'address':hex(obj)});continue
    m=u64(obj+0x10);raw=read(m,68);row={'slot':i,'address':hex(obj),'flags':hex(u32(obj+4)),'matrix':struct.unpack_from('<16f',raw),'matrix_flags':struct.unpack_from('<I',raw,64)[0]}
    # Native140b49ba0 write gates and1409ce210 actual linked parent/local.
    row['update_flags_u32']=u32(obj+8)
    modifier=u64(obj+0x28)
    row['modifier_address']=hex(modifier)
    if modifier:
     row['modifier_flags_u16_56']=struct.unpack('<H',read(modifier+0x56,2))[0]
    link_visual=u64(obj+0x20)
    linked=u64(link_visual+0x10) if link_visual else 0
    if linked:
     row['linked_parent_address']=hex(u64(linked+8))
     local=read(linked+0x10,68)
     row['linked_local_matrix']=struct.unpack_from('<16f',local)
     row['linked_local_matrix_flags']=struct.unpack_from('<I',local,64)[0]
    if i in (27,28):row['modifier24_records']=capture_modifier24(read,obj)
    obj_visual=u64(obj+0x20);geometry=u64(u64(obj_visual)) if obj_visual and u64(obj_visual) else 0
    if geometry:
     words=struct.unpack('<8I',read(geometry,32));row['geometry_header']={'address':hex(geometry),'first_words':words}
     nv=words[4];vertex_data=u64(geometry+0x18)
     if 0<nv<=5461 and vertex_data:
      pending_geometry.append((row,vertex_data,nv))
    objects.append(row)
   result['pose_consistency']={'component_prefix_unchanged':read(component,0xbc)==state,
                             'clips':{},'atomic_frame_proven':False}
   result['pose_consistency']['modifier24_states_unchanged']=check_modifier24_records(read,
    [record for obj in objects for record in obj.get('modifier24_records',[])])
   for name,cache in prepared_clips.items():
    entry=result['animation_state']['instances'][name]
    check=check_clip_prefix(read,int(entry['clip_link_address'],16),cache)
    check['instance_header_unchanged']=read(int(entry['address'],16),0x5c).hex()==entry['raw_header_hex']
    result['pose_consistency']['clips'][name]=check
   update_pass_after=u32(relocated(0x1419a1480))
   result['pose_consistency']['update_pass_counter']={
    'before':update_pass_before,'after':update_pass_after,
    'unchanged':update_pass_before==update_pass_after,
    'evidence':'1409adf00 increments DWORD1419a1480 at1409ae449',
    'limitation':'World update pass marker, not proven to be a unique rendered/gameplay frame counter.'}
   result['pose_read_window_ms']=(time.perf_counter()-pose_started)*1000
   result['capture_order']='actor/palette, prepared clip states, bone matrices, clip payloads, geometry'
   for name,cache in prepared_clips.items():
    entry=result['animation_state']['instances'][name]
    entry['clip_link']=capture_clip_link(read,int(entry['clip_link_address'],16),prepared_reads=cache)
   for row,vertex_data,nv in pending_geometry:
    row['geometry_positions']=[list(v) for v in struct.iter_unpack('<3f',read(vertex_data,nv*12))]
   result['objects']=objects;result['status']='captured'
  out=report_path('stage4-sally-runtime-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json');out.write_text(json.dumps(result,indent=2));print(json.dumps({'report':str(out),'status':result['status'],'globals':result['globals'],'palette_count':result.get('palette',{}).get('count')}))
 finally:kernel.CloseHandle(handle)
if __name__=='__main__':main()
