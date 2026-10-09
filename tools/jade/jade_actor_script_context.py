"""Bounded actor-owned AI context observation, based on140b29720.

Global1420c3490 is saved/restored by callbacks: it does not identify a
permanent Sally context. No script is executed and no memory is written.
"""
import struct


def capture_actor_script_context(read, actor, *, max_callbacks=512):
    def pointer(address):
        return struct.unpack('<Q', read(address, 8))[0]

    def callback_record(address):
        if address == 0:
            return {'address': '0x0'}
        if address < 0x10000:
            raise ValueError('Invalid callback record pointer')
        raw = read(address, 0x38)
        return {'address': hex(address), 'entry_address': hex(struct.unpack_from('<Q', raw)[0]),
                'native_function_address': hex(struct.unpack_from('<Q', raw, 0x20)[0]),
                'raw_hex': raw.hex()}

    if actor < 0x10000 or not 0 < max_callbacks <= 512:
        raise ValueError('Expected resolved actor and bounded callback limit')
    result = {'actor_address': hex(actor), 'limits': [
        'Unsynchronised persistent data; no proof of callback execution.',
        'Inherited/extra callbacks may select a different owner actor.']}
    modifier = pointer(actor + 0x28)
    result['modifier_address'] = hex(modifier)
    if modifier == 0:
        result['status'] = 'no_modifier'
        return result
    if modifier < 0x10000:
        raise ValueError('Invalid modifier pointer')
    context = pointer(modifier + 8)
    result['context_address'] = hex(context)
    if context == 0:
        result['status'] = 'no_script_context'
        return result
    if context < 0x10000:
        raise ValueError('Invalid script context pointer')
    header = read(context, 0xa0)
    shared = struct.unpack_from('<Q', header)[0]
    brain = struct.unpack_from('<Q', header, 0x78)[0]
    vm = struct.unpack_from('<Q', header, 0x88)[0]
    result.update(shared_address=hex(shared), brain_address=hex(brain),
                  vm_context_address=hex(vm), context_raw_hex=header.hex())
    if brain >= 0x10000:
        raw = read(brain + 0x604, 28)
        result['tracking_brain'] = {
            'raw_604_61f_hex': raw.hex(), 'base_word_604': struct.unpack_from('<I', raw)[0],
            'target_handle_608': struct.unpack_from('<I', raw, 4)[0],
            'target_offset_60c': struct.unpack_from('<3f', raw, 8),
            'tracking_word_618': struct.unpack_from('<I', raw, 20)[0],
            'strength_61c': struct.unpack_from('<f', raw, 24)[0]}
    if shared >= 0x10000:
        descriptor = pointer(shared)
        result['descriptor_address'] = hex(descriptor)
        if descriptor >= 0x10000:
            count = struct.unpack('<i', read(descriptor + 0x58, 4))[0]
            if not 0 <= count <= max_callbacks:
                raise ValueError('Shared callback count outside capture bounds')
            table = pointer(descriptor + 0x60)
            if count and table < 0x10000:
                raise ValueError('Absent shared callback table')
            result['shared_callbacks'] = [dict(index=i, **callback_record(pointer(table+i*8)))
                                          for i in range(count)]
    count = struct.unpack_from('<i', header, 0x90)[0]
    table = struct.unpack_from('<Q', header, 0x98)[0]
    if not 0 <= count <= max_callbacks:
        raise ValueError('Extra callback count outside capture bounds')
    if count and table < 0x10000:
        raise ValueError('Absent extra callback table')
    result['extra_callbacks'] = []
    for i in range(count):
        record, callback_index, owner = struct.unpack('<Qi4xQ', read(table+i*24, 24))
        result['extra_callbacks'].append(dict(callback_index=callback_index,
                                              owner_actor_address=hex(owner),
                                              **callback_record(record)))
    result['status'] = 'captured'
    return result
