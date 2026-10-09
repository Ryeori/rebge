"""Compare captured mutable clip prefix after reading a pose, without writes."""
import struct


def check_clip_prefix(read,link,prepared):
    descriptor=prepared[link,16]
    resource,states=struct.unpack('<QQ',descriptor)
    header=prepared[resource,16]
    count=struct.unpack_from('<H',header,8)[0]
    before=prepared[states,count*12] if count else b''
    after=read(states,count*12) if count else b''
    return dict(states_before_hex=before.hex(),states_after_hex=after.hex(),
                states_unchanged=before==after,
                link_unchanged=read(link,16)==descriptor,
                resource_unchanged=read(resource,16)==header,
                limitation='Equal bytes do not prove atomic reads or callback ordering.')
