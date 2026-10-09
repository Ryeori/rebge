import struct
import unittest
from jade_actions import decode_action, encode_action


class ActionTests(unittest.TestCase):
    def test_truncated_records_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Truncated action records'):
            decode_action(bytes([2, 0, 0, 0]) + bytes(20))

    def test_edit_preserves_unrelated_and_opaque_bytes(self):
        raw = (bytes([1, 0xAB, 0xCD, 0xEF]) +
               struct.pack('<III4BHBB', 0x7100B0E7, 0xFFFFFFFF, 0x12345678,
                           3, 4, 5, 6, 0xABCD, 0xFE, 0x81) +
               bytes.fromhex('0000ff807fc520803f'))
        action = decode_action(raw)
        action['records'][0]['resource_key'] = '7100B0E8'
        edited = encode_action(action)
        self.assertEqual(edited[:4], raw[:4])
        self.assertEqual(edited[8:], raw[8:])
        self.assertEqual(struct.unpack_from('<I', edited, 4)[0], 0x7100B0E8)

    def test_empty_action_retains_tail(self):
        raw = bytes.fromhex('00ff1234000180ff')
        self.assertEqual(encode_action(decode_action(raw)), raw)


if __name__ == '__main__':
    unittest.main()
