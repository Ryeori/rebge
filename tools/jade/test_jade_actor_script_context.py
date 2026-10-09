import struct
import unittest

from jade_actor_script_context import capture_actor_script_context


class ActorContextTests(unittest.TestCase):
    def setUp(self):
        self.memory = bytearray(0x80000)
        self.actor, self.modifier, self.context = 0x10000, 0x11000, 0x12000
        self.put(self.actor+0x28, '<Q', self.modifier)
        self.put(self.modifier+8, '<Q', self.context)
        self.put(self.context, '<Q', 0x13000)
        self.put(0x13000, '<Q', 0x14000)
        self.put(self.context+0x78, '<Q', 0x20000)
        self.put(self.context+0x88, '<Q', 0x21000)
        self.put(0x20604, '<II3fIf', 3, 0x10002, 1, 2, 3, 0x4000000, 0.5)
        self.put(0x14058, '<i', 1)
        self.put(0x14060, '<Q', 0x15000)
        self.put(0x15000, '<Q', 0x16000)
        self.put(0x16020, '<Q', 0x140e02760)
        self.put(self.context+0x90, '<i', 1)
        self.put(self.context+0x98, '<Q', 0x17000)
        self.put(0x17000, '<Qi4xQ', 0x18000, 7, 0x19000)

    def put(self, address, fmt, *values):
        struct.pack_into(fmt, self.memory, address, *values)

    def read(self, address, size):
        return bytes(self.memory[address:address+size])

    def test_actor_owned_context_and_extra_owner_are_distinct(self):
        result = capture_actor_script_context(self.read, self.actor)
        self.assertEqual(result['context_address'], '0x12000')
        self.assertEqual(result['tracking_brain']['strength_61c'], 0.5)
        self.assertEqual(result['shared_callbacks'][0]['native_function_address'], '0x140e02760')
        self.assertEqual(result['extra_callbacks'][0]['owner_actor_address'], '0x19000')
        self.assertEqual(result['extra_callbacks'][0]['callback_index'], 7)

    def test_bounded_count_rejects_corrupt_table_before_read(self):
        self.put(0x14058, '<i', 513)
        with self.assertRaises(ValueError):
            capture_actor_script_context(self.read, self.actor)

    def test_missing_modifier_does_not_follow_null(self):
        self.put(self.actor+0x28, '<Q', 0)
        self.assertEqual(capture_actor_script_context(self.read, self.actor)['status'], 'no_modifier')


if __name__ == '__main__':
    unittest.main()
