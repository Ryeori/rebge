"""Bounded retained-transition phase lookup used by1409b3b20.

Table is component+98, action index is instance+54, phase index instance+56.
Missing native entries return None flags; never substitute the primary phase.
"""
import struct


def capture_phase_descriptor(read, address):
    """1409bdbc0 header8 + phase records32; retain raw pointers and bytes.

    Repeat byte is descriptor+phase*32+0x20, normalized0->1 by loader.
    Raw record storage, unlike flags/control alone, permits a repeat decision.
    """
    if address == 0:
        return dict(address='0x0', present=False)
    if address < 0x10000:
        raise ValueError('Invalid phase descriptor pointer')
    header = read(address, 8)
    if len(header) != 8:
        raise ValueError('Truncated phase descriptor header')
    count = header[0]
    raw = read(address, 8 + count * 32)
    if len(raw) != 8 + count * 32:
        raise ValueError('Truncated phase descriptor records')
    if raw[:8] != header:
        raise ValueError('Phase descriptor changed while reading')
    records = []
    for index in range(count):
        record = raw[8 + index * 32:40 + index * 32]
        records.append(dict(index=index, clip_address=hex(struct.unpack_from('<Q', record)[0]),
            repeat_limit=record[24], speed_source_byte=record[26], flags=record[27],
            control=struct.unpack_from('<H', record, 28)[0], raw_hex=record.hex()))
    return dict(address=hex(address), present=True, phase_count=count,
                loop_phase=raw[1], raw_hex=raw.hex(), records=records)


def transition_phase(read,action_table,header):
    if len(header)<0x57:raise ValueError('Transition header truncated')
    action=struct.unpack_from('<H',header,0x54)[0];phase=header[0x56]
    result=dict(action_index=action,phase_index=phase,flags=None,control=None)
    if action_table<0x10000:return result
    count=struct.unpack('<H',read(action_table,2))[0]
    if count>4096:raise ValueError('Unexpected action count')
    if action>=count:return result
    descriptor=struct.unpack('<Q',read(action_table+16+action*8,8))[0]
    if descriptor<0x10000:return result
    phase_count=read(descriptor,1)[0]
    if phase>=phase_count:return result
    raw=read(descriptor+phase*32+0x23,3)
    result.update(descriptor_address=hex(descriptor),flags=raw[0],
                  control=struct.unpack_from('<H',raw,1)[0])
    return result
