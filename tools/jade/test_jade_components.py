from project_paths import PROJECT_ROOT, report_path
import struct
import unittest
from jade_components import parse_component4, parse_component20


class Components(unittest.TestCase):
    def test_component20_conditional_length(self):
        for sentinel, expected in ((1.001, 68), (0.0, 44)):
            data = struct.pack('<6I4f', 20, 0, 4, 29, 0xffffffff,
                               0xffffffff, .2, 1, .5, sentinel)
            if sentinel:
                data += struct.pack('<6f', 1, 2, 3, 4, 5, 6)
            data += struct.pack('<fI', .5, 0xffffffff)
            parsed = parse_component20(data, 0)
            self.assertEqual(parsed['end_offset'], expected)
            self.assertEqual(len(parsed['vectors']), 2 if sentinel else 0)
            self.assertEqual(struct.unpack_from('<I', data, expected)[0], 0xffffffff)
            with self.assertRaises(ValueError):
                parse_component20(data[:expected-1], 0)

    def test_component4_indices_and_bit_preservation(self):
        header = struct.pack('<7I', 4, 0, 0, 0, 1, 1, 1)
        group = struct.pack('<I', 1) + bytes(64)
        group += struct.pack('<4I', 0, 0x80000000, 0x7fc01234, 0x3f800000)
        secondary = struct.pack('<3I', 1, 0x3f800000, 0)
        data = header + group + secondary + bytes(64) + struct.pack('<I', 0)
        parsed = parse_component4(data, 0)
        self.assertEqual(parsed['end_offset'], len(data))
        self.assertEqual(parsed['primary'][0]['words'][0],
                         (0x80000000, 0x7fc01234, 0x3f800000))
        with self.assertRaises(ValueError):
            parse_component4(data[:-1], 0)


if __name__ == '__main__':
    unittest.main()
