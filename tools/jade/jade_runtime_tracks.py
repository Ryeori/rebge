"""Bounded native clip-link snapshots; offsets proven by 1532461d0/140b28360.

Caller supplies a read-only memory reader. Asset identity and track type are
not inferred from pointers or flags.
"""
import struct


def decode_runtime_transform(flags, payload):
    """Only native decoded quaternion/vector representations of known size."""
    if (flags & 0x780 or flags & 0x14 == 0x10) and len(payload) == 16:
        return {'quaternion_xyzw': list(struct.unpack('<4f', payload))}
    if flags & 0xf800 and len(payload) == 12:
        return {'vector_xyz': list(struct.unpack('<3f', payload))}
    return {}


def prepare_clip_reads(read, link_address, *, max_tracks=512):
    """Capture mutable link/descriptor/track states before slow payload reads.

    Cache is private bytes keyed by exact address/length, not a memory freeze.
    Frame payloads remain unsynchronised and are decoded later.
    """
    cache = {}
    def remember(address,size):
        data=read(address,size)
        cache[address,size]=data
        return data
    if link_address < 0x10000:
        return cache
    resource,states=struct.unpack('<QQ',remember(link_address,16))
    if resource < 0x10000 or states < 0x10000:
        return cache
    descriptor=remember(resource,16)
    tracks=struct.unpack_from('<Q',descriptor)[0]
    count=struct.unpack_from('<H',descriptor,8)[0]
    if count > max_tracks:
        raise ValueError('Native track count exceeds bounded snapshot limit')
    if count:
        if tracks < 0x10000:
            raise ValueError('Absent native track array')
        remember(tracks,count*40)
        remember(states,count*12)
    return cache


def capture_clip_link(read, link_address, *, max_tracks=512, prepared_reads=None,
                      include_payloads=True):
    if prepared_reads is not None:
        live_read=read
        def read(address,size):
            cached=prepared_reads.get((address,size))
            return cached if cached is not None else live_read(address,size)
    if link_address < 0x10000:
        return {'status': 'absent'}
    resource, states = struct.unpack('<QQ', read(link_address, 16))
    result = {'resource_address': hex(resource), 'states_address': hex(states)}
    if resource < 0x10000 or states < 0x10000:
        return {**result, 'status': 'incomplete'}
    descriptor = read(resource, 16)
    tracks = struct.unpack_from('<Q', descriptor)[0]
    count, flags = struct.unpack_from('<HH', descriptor, 8)
    if count > max_tracks:
        raise ValueError('Native track count exceeds bounded snapshot limit')
    if count and tracks < 0x10000:
        raise ValueError('Absent native track array')
    rows = []
    if count:
        definitions = read(tracks, count * 40)
        runtime = read(states, count * 12)
        for index in range(count):
            definition = definitions[index*40:(index+1)*40]
            elapsed, auxiliary, frame_index, state_flags = struct.unpack_from('<ffHH', runtime, index*12)
            actor, frames = struct.unpack_from('<QQ', definition)
            payload_pool = struct.unpack_from('<Q', definition, 16)[0]
            payload_cursor = 0
            frame_count, track_flags, indexed_slot, auxiliary_short = struct.unpack_from('<4H', definition, 28)
            if frame_count > 2730:
                raise ValueError('Frame array exceeds bounded snapshot limit')
            frame_headers = []
            if frame_count and frames >= 0x10000:
                raw_frames = read(frames, frame_count * 24)
                frame_headers = [{'tick_raw': struct.unpack_from('<H', raw_frames, j*24)[0],
                                  'flags': struct.unpack_from('<H', raw_frames, j*24+2)[0]}
                                 for j in range(frame_count)]
                for j, header in enumerate(frame_headers):
                    if not include_payloads:
                        continue
                    if header['flags'] & 0x7c0 != 0x80 or header['flags'] & 0x20:
                        # Events/reference transforms do not share this decoder.
                        if header['flags'] & 0x7c0 == 0x40:
                            payload_pool = 0  # Mixed pool cursor remains unverified.
                        continue
                    value = struct.unpack_from('<Q', raw_frames, j*24+8)[0]
                    if value & 1:
                        declared = (value & 0xffff) >> 1
                        flags = (value >> 16) & 0xffff
                        size = declared - 4
                        address = payload_pool + payload_cursor if payload_pool else 0
                        payload_cursor += max(size, 0)
                    elif value >= 0x10000:
                        declared, flags = struct.unpack('<HH', read(value, 4))
                        size, address = declared - 4, value + 4
                    else:
                        continue
                    if not 0 <= size <= 1024:
                        raise ValueError('Transform payload exceeds bounded size')
                    header.update(transform_flags=flags, runtime_declared_size=declared)
                    if address and size:
                        payload = read(address, size)
                        header['runtime_payload_hex'] = payload.hex()
                        header.update(decode_runtime_transform(flags, payload))
            rows.append({'track_index': index, 'actor_address': hex(actor),
                         'frames_address': hex(frames), 'frame_count': frame_count,
                         'track_flags': track_flags, 'auxiliary_short_u16': auxiliary_short,
                         'indexed_slot': indexed_slot, 'elapsed_seconds': elapsed,
                         'auxiliary_f32': auxiliary, 'frame_index': frame_index,
                         'state_flags': state_flags, 'frame_headers': frame_headers})
    return {**result, 'status': 'captured', 'track_count': count,
            'resource_flags': flags, 'tracks': rows,
            'mutable_prefix_prepared': prepared_reads is not None,
            'payloads_included': include_payloads}
