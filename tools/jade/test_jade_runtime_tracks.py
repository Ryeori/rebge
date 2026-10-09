import struct
import unittest
from jade_runtime_tracks import capture_clip_link, decode_runtime_transform, prepare_clip_reads


class RuntimeTrackTests(unittest.TestCase):
    def memory(self, count=1):
        track = bytearray(40)
        struct.pack_into('<QQ', track, 0, 0x60000, 0x70000)
        struct.pack_into('<4H', track, 28, 9, 0x8003, 255, 12)
        blocks = {0x10000: struct.pack('<QQ', 0x20000, 0x30000),
                  0x20000: struct.pack('<QHHI', 0x40000, count, 2, 0),
                  0x40000: bytes(track),
                  0x30000: struct.pack('<ffHH', 0.125, 0.75, 3, 5),
                  0x70000: struct.pack('<HH20x', 12, 128)*9}
        def read(address, size):
            value = blocks[address]
            if len(value) != size:
                raise ValueError('Unexpected memory read length')
            return value
        return read

    def test_definition_and_state_arrays_have_distinct_strides(self):
        result = capture_clip_link(self.memory(), 0x10000)
        row = result['tracks'][0]
        self.assertEqual(row['indexed_slot'], 255)
        self.assertEqual(row['auxiliary_short_u16'], 12)
        self.assertEqual(row['frame_count'], 9)
        self.assertEqual(row['frame_index'], 3)
        self.assertEqual(row['elapsed_seconds'], 0.125)
        self.assertEqual(row['auxiliary_f32'], 0.75)
        self.assertEqual(row['frame_headers'][0]['tick_raw'], 12)

    def test_oversized_count_rejected_before_array_reads(self):
        with self.assertRaises(ValueError):
            capture_clip_link(self.memory(513), 0x10000)

    def test_absent_link_does_not_read_memory(self):
        self.assertEqual(capture_clip_link(None, 0)['status'], 'absent')

    def test_deferred_payload_keeps_prepared_state(self):
        original=self.memory()
        cache=prepare_clip_reads(original,0x10000)
        def later_read(address,size):
            if address in (0x10000,0x20000,0x30000,0x40000):
                self.fail('Mutable prefix should not be reread after payload delay')
            return original(address,size)
        result=capture_clip_link(later_read,0x10000,prepared_reads=cache)
        self.assertEqual(result['tracks'][0]['elapsed_seconds'],0.125)
        self.assertEqual(result['tracks'][0]['frame_index'],3)
        self.assertTrue(result['mutable_prefix_prepared'])

    def test_header_only_capture_does_not_fetch_transform_payloads(self):
        original=self.memory()
        def read(address,size):
            if address==0x70000:
                return struct.pack('<HH4xQ8x',12,128,0x90000)*9
            if address==0x90000:
                self.fail('Header-only observation must not read transform payload')
            return original(address,size)
        result=capture_clip_link(read,0x10000,include_payloads=False)
        self.assertFalse(result['payloads_included'])
        self.assertEqual(len(result['tracks'][0]['frame_headers']),9)

    def test_uncompressed_quaternion_flag16(self):
        payload = struct.pack('<4f', -0.125, 0.5, 0.25, 0.75)
        self.assertEqual(decode_runtime_transform(16, payload)['quaternion_xyzw'],
                         [-0.125, 0.5, 0.25, 0.75])
        self.assertEqual(decode_runtime_transform(16, payload[:12]), {})

    def test_inline_rotation_tag_reads_payload_pool(self):
        base_read = self.memory()
        def read(address, size):
            if address == 0x40000:
                data = bytearray(base_read(address, size))
                struct.pack_into('<Q', data, 16, 0x80000)
                return bytes(data)
            if address == 0x70000:
                # Loader writes 0x29 (20-byte logical header+quaternion) into
                # frame+8 and transform flags into frame+10.
                frame = struct.pack('<HH4xQ8x', 12, 128, 0x900029)
                return frame * 9
            if 0x80000 <= address < 0x80000+9*16:
                self.assertEqual(size, 16)
                return struct.pack('<4f', 0, 0, 0, 1)
            return base_read(address, size)
        result = capture_clip_link(read, 0x10000)
        self.assertEqual(result['tracks'][0]['frame_headers'][8]['quaternion_xyzw'], [0, 0, 0, 1])


if __name__ == '__main__':
    unittest.main()
