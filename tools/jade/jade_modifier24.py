"""Modifier type0x18 (decimal24): source payload and bounded runtime state.

Native factory table1419a14a0 + type*0x38; payload reader153ca5d50,
state allocation153cada40, world writer1409dcba0. Names are reconstructed.
"""
import math
import struct
from jade_animation_transition import f32
from jade_target_hierarchy import IDENTITY,raw_affine_product


def effective_mode_flags(mode,parent_present):
    """1409dcba0 clears linked-position8 without parent, and rotation2 with8."""
    if not parent_present:mode &= ~8
    if mode&8:mode &= ~2
    return mode


def _unit(vector):
    x,y,z=map(f32,vector)
    squared=f32(f32(f32(y*y)+f32(x*x))+f32(z*z))
    if not math.isfinite(squared) or squared<=0:raise ValueError('Degenerate modifier direction')
    inverse=f32(1/f32(math.sqrt(squared)))
    return [f32(v*inverse) for v in (x,y,z)]


def _length(vector):
    x,y,z=map(f32,vector)
    squared=f32(f32(f32(y*y)+f32(x*x))+f32(z*z))
    if not math.isfinite(squared) or squared<0:raise ValueError('Invalid modifier direction length')
    return f32(math.sqrt(squared))


def _lag_quaternion(original,lagged):
    original=_unit(original);lagged=_unit(lagged)
    half=_unit([f32(a+b) for a,b in zip(original,lagged)])
    return [f32(f32(half[2]*original[1])-f32(half[1]*original[2])),
            f32(f32(half[0]*original[2])-f32(half[2]*original[0])),
            f32(f32(half[1]*original[0])-f32(half[0]*original[1])),
            f32(f32(f32(half[1]*original[1])+f32(half[0]*original[0]))+f32(half[2]*original[2]))]


def _quaternion_matrix(q):
    """140aed650 arithmetic order; no quaternion renormalization."""
    x,y,z,w=map(f32,q);xx=f32(x+x);yy=f32(y+y);zz=f32(z+z)
    a=f32(.5-f32(xx*x));b=f32(.5-f32(yy*y));c=f32(.5-f32(zz*z))
    zw=f32(zz*w);result=IDENTITY.copy()
    result[0]=f32(c+b);result[5]=f32(c+a);result[10]=f32(b+a)
    result[4]=f32(f32(xx*y)-zw);result[1]=f32(zw+f32(xx*y))
    result[8]=f32(f32(yy*w)+f32(xx*z));result[2]=f32(f32(xx*z)-f32(yy*w))
    result[9]=f32(f32(yy*z)-f32(xx*w));result[6]=f32(f32(yy*z)+f32(xx*w))
    return result


def lag_pose_from_position(nominal_world,world_flags,parent_world,smoothed_position):
    """Restricted linked8 directional correction from observed final position.

    This is a diagnostic reconstruction: native computes the quaternion before
    storing its length-corrected position, so last-bit agreement is not assumed.
    Antiparallel/zero directions and scaled matrices are rejected.
    """
    if world_flags&8:raise NotImplementedError('Scaled lag-pose reconstruction')
    original=[f32(nominal_world[12+i]-parent_world[12+i]) for i in range(3)]
    lagged=[f32(smoothed_position[i]-parent_world[12+i]) for i in range(3)]
    q=_lag_quaternion(original,lagged)
    result,flags=raw_affine_product(nominal_world,_quaternion_matrix(q),world_flags,4)
    result[12:15]=list(map(f32,smoothed_position))
    return result,flags


def modifier24_step(state_bytes,nominal_world,world_flags,parent_world,parent_flags,delta_time):
    """Restricted1409dcba0 no-scale evaluation with explicit prior state.

    Supports ordinary position/orientation smoothing and linked lag constraints.
    The caller must supply actual writer inputs; adjacent final snapshots do not
    automatically establish those inputs. Alternate evaluator1000 is rejected.
    """
    from jade_basis_normalize import normalize_basis
    if len(state_bytes)!=256:raise ValueError('Expected native modifier state256bytes')
    if world_flags&8 or parent_flags&8:raise NotImplementedError('Scaled modifier evaluation')
    if any(len(m)!=16 or not all(math.isfinite(v) for v in m)
           for m in (nominal_world,)+( (parent_world,) if parent_world is not None else ())):
        raise ValueError('Expected finite native input matrices')
    state=bytearray(state_bytes);mode=struct.unpack_from('<I',state,4)[0]
    if mode&0x1000:raise NotImplementedError('Alternate modifier evaluator')
    mode=effective_mode_flags(mode,parent_world is not None)
    weight=damping_weight(struct.unpack_from('<f',state,8)[0],delta_time)
    result=list(map(f32,nominal_world))
    if mode&9:
        previous=list(struct.unpack_from('<3f',state,0x88))
        if any(math.isnan(v) for v in previous):previous=[0.,0.,0.]
        if not all(math.isfinite(v) for v in previous):raise NotImplementedError('Infinite modifier history unsupported')
        position=[f32(f32(f32(result[12+i]-previous[i])*weight)+previous[i]) for i in range(3)]
        if mode&8:
            height=struct.unpack_from('<f',state,0xd8)[0]
            if not math.isfinite(height):raise ValueError('Non-finite modifier height')
            position[2]=f32(f32(weight*height)+position[2])
            if mode&0x400:
                local=struct.unpack_from('<16fI',state,0xc)
                base,_=raw_affine_product(local[:16],parent_world,local[16],parent_flags)
                delta=[f32(position[i]-base[12+i]) for i in range(3)]
                low=struct.unpack_from('<3f',state,0xa8);high=struct.unpack_from('<3f',state,0xb4)
                coordinates=[]
                for column in (0,4,8):
                    value=f32(f32(f32(delta[1]*base[column+1])+f32(delta[0]*base[column]))+f32(delta[2]*base[column+2]))
                    index=column//4
                    coordinates.append(f32(min(high[index],max(low[index],value))))
                position=[]
                for row in range(3):
                    value=f32(f32(f32(base[4+row]*coordinates[1])+f32(base[row]*coordinates[0]))+f32(base[8+row]*coordinates[2]))
                    position.append(f32(value+base[12+row]))
            original=[f32(result[12+i]-parent_world[12+i]) for i in range(3)]
            lagged=[f32(position[i]-parent_world[12+i]) for i in range(3)]
            original_length=_length(original);lagged_length=_length(lagged)
            if lagged_length:
                ratio=f32(original_length/lagged_length)
                position=[f32(f32(ratio*lagged[i])+parent_world[12+i]) for i in range(3)]
                if original_length:
                    result,world_flags=raw_affine_product(result,_quaternion_matrix(_lag_quaternion(original,lagged)),world_flags,4)
        struct.pack_into('<3f',state,0x88,*position);result[12:15]=position
    if mode&2:
        basis=list(struct.unpack_from('<16f',state,0x58))
        for i in (0,1,2,4,5,6,8,9,10):basis[i]=f32(f32(f32(result[i]-basis[i])*weight)+basis[i])
        basis=normalize_basis(basis);struct.pack_into('<16f',state,0x58,*basis)
        for i in (0,1,2,4,5,6,8,9,10):result[i]=basis[i]
    return dict(state_bytes=bytes(state),world_matrix=result,world_flags=world_flags,
                effective_mode_flags=mode,weight=weight,
                limitation='Restricted numerical step; input age and palette publication not inferred.')


def prepare_modifier24_state(state_bytes,local_matrix,local_flags):
    """1409ddef0 saves parameters and pre-correction linked local."""
    if len(state_bytes)!=256:raise ValueError('Expected native modifier state256bytes')
    state=bytearray(state_bytes)
    for source,destination,size in ((4,0x50,4),(8,0x54,4),(0xd8,0xdc,4),
        (0xec,0xf0,4),(0xa8,0xc0,12),(0xb4,0xcc,12)):
        state[destination:destination+size]=state[source:source+size]
    struct.pack_into('<16fI',state,0xc,*local_matrix,local_flags)
    return bytes(state)


def finalize_modifier24_state(state_bytes):
    """1409ddda0 restores parameters/local; lag state and published world stay.

    Actual native finalizer walks a global processed list. This evaluates one
    explicitly supplied processed node and never infers list membership.
    """
    if len(state_bytes)!=256:raise ValueError('Expected native modifier state256bytes')
    state=bytearray(state_bytes)
    for source,destination,size in ((0x54,8,4),(0xdc,0xd8,4),(0xf0,0xec,4),
        (0xc0,0xa8,12),(0xcc,0xb4,12)):
        state[destination:destination+size]=state[source:source+size]
    mode=struct.unpack_from('<I',state,0x50)[0]&~0x10000000
    struct.pack_into('<I',state,4,mode)
    local=struct.unpack_from('<16fI',state,0xc)
    return dict(state_bytes=bytes(state),local_matrix=list(local[:16]),local_flags=local[16])


def decode_source_record(data):
    if len(data)<24:raise ValueError('Truncated modifier record')
    kind,record_flags,length,version=struct.unpack_from('<4I',data)
    if kind!=24:raise NotImplementedError('Expected modifier type0x18')
    if version not in (0,1,2,3):raise NotImplementedError('Unsupported source payload version')
    expected=12+(24 if version else 0)+(4 if version>=2 else 0)+(4 if version>=3 else 0)
    if length!=expected or len(data)<12+length+4:raise ValueError('Invalid serialized payload length')
    damping,flags=struct.unpack_from('<fI',data,16)
    if not math.isfinite(damping):raise ValueError('Non-finite damping value')
    offset=24
    bounds=list(struct.unpack_from('<6f',data,offset)) if version else [-1.,-1.,-1.,1.,1.,1.]
    if version:offset+=24
    if not all(math.isfinite(v) for v in bounds):raise ValueError('Non-finite bounds')
    height=struct.unpack_from('<f',data,offset)[0] if version>=2 else None
    if version>=2:offset+=4
    value_ec=struct.unpack_from('<f',data,offset)[0] if version>=3 else None
    if version>=3:offset+=4
    if struct.unpack_from('<I',data,offset)[0]!=0xffffffff:
        raise NotImplementedError('Additional modifier records require their own readers')
    return dict(type=kind,record_flags=record_flags,payload_version=version,
        damping=damping,mode_flags=flags,bounds_min=bounds[:3],bounds_max=bounds[3:],
        height_d8=height,value_ec=value_ec,consumed_bytes=offset+4,
        source_record_hex=data[:offset+4].hex())


def encode_source_record(record):
    version=record['payload_version']
    if version not in (0,1,2,3):raise NotImplementedError('Unsupported source payload version')
    payload=struct.pack('<IfI',version,record['damping'],record['mode_flags'])
    if version:payload+=struct.pack('<6f',*record['bounds_min'],*record['bounds_max'])
    if version>=2:payload+=struct.pack('<f',record['height_d8'])
    if version>=3:payload+=struct.pack('<f',record['value_ec'])
    return struct.pack('<3I',24,record['record_flags'],len(payload))+payload+struct.pack('<I',0xffffffff)


def damping_weight(damping,delta_time,*,max_iterations=4096):
    """1409dcba0 repeated f32 attenuation, with an explicit bounded delta."""
    damping,delta_time=map(f32,(damping,delta_time))
    if not all(math.isfinite(x) for x in (damping,delta_time)):raise ValueError('Expected finite inputs')
    quantum=struct.unpack('<f',bytes.fromhex('0e745a3b'))[0]
    loss=f32(max(0,f32(1-damping)));factor=f32(1-f32(loss*loss))
    elapsed=f32(0);retained=f32(1);iterations=0
    while elapsed<delta_time:
        if iterations>=max_iterations:raise ValueError('Delta exceeds bounded modifier evaluation')
        elapsed=f32(elapsed+quantum);retained=f32(retained*factor);iterations+=1
    return f32(1-retained)


def capture_modifier24(read,actor_address,*,max_records=32):
    """Read linked component records; no game memory writes or execution."""
    if not 1<=max_records<=64:raise ValueError('Invalid modifier-list bound')
    pointer=lambda address:struct.unpack('<Q',read(address,8))[0]
    owner_modifier=pointer(actor_address+0x28)
    if not owner_modifier:return []
    address=pointer(owner_modifier+0x38);records=[];seen=set()
    while address:
        if address in seen or len(seen)>=max_records:raise ValueError('Cyclic or excessive modifier list')
        seen.add(address);header=read(address,0x38)
        table=struct.unpack_from('<Q',header,0)[0]
        kind=struct.unpack('<I',read(table,4))[0]
        if kind==24:
            state_address=struct.unpack_from('<Q',header,0x10)[0]
            state=read(state_address,0x100)
            records.append(dict(address=hex(address),table_address=hex(table),
                header_hex=header.hex(),
                record_flags=struct.unpack_from('<I',header,8)[0],
                state_address=hex(state_address),state_hex=state.hex(),
                header_unchanged=read(address,0x38)==header,
                state_unchanged=read(state_address,0x100)==state))
        address=struct.unpack_from('<Q',header,0x18)[0]
    return records


def check_modifier24_records(read,records):
    """Repeat all state/header reads at the end of the pose read window."""
    return all(record['header_unchanged'] and record['state_unchanged']
        and read(int(record['address'],16),0x38).hex()==record['header_hex']
        and read(int(record['state_address'],16),0x100).hex()==record['state_hex']
        for record in records)
