import struct
import unittest

from jade_tracking_target import (variable_storage, resolve_actor_reference,
                                  direct_target_position)


class TargetTests(unittest.TestCase):
    def test_descriptor_types_and_element_addressing(self):
        for kind, stride in ((0x27, 8), (0x28, 8), (0x2b, 8),
                             (0x2f, 8), (0x29, 64), (0x26, 0)):
            blocks = {0x10000: struct.pack('<QQQ', 0x20000, 0, 0x30000),
                      0x20018: struct.pack('<IIhH', 20, 0, kind, 0)}
            self.assertEqual(variable_storage(lambda a, n: blocks[a],
                                             (2 << 16) | 3, 0x10000,
                                             max_descriptors=3),
                             0x30000 + 20 + 3 * stride)

    def test_descriptor_bounds_precede_read(self):
        def forbidden(*args):
            self.fail('Out-of-range descriptor must not be read')
        with self.assertRaises(ValueError):
            variable_storage(forbidden, 3 << 16, 0x10000, max_descriptors=3)

    def test_reference_table_and_null(self):
        refs = (0x40000, 0)
        self.assertEqual(resolve_actor_reference(1, refs), 0x40000)
        self.assertEqual(resolve_actor_reference(2, refs), 0)
        self.assertEqual(resolve_actor_reference(0x50000, refs), 0x50000)
        self.assertEqual(direct_target_position(None, 0), (0, 0, 0))

    def test_world_matrix_translation(self):
        blocks = {0x40004: struct.pack('<I', 2),
                  0x40010: struct.pack('<Q', 0x50000),
                  0x50030: struct.pack('<3f', 1.25, -2, 3.5)}
        self.assertEqual(direct_target_position(lambda a, n: blocks[a], 0x40000),
                         (1.25, -2, 3.5))

    def test_linked_branch_rejected(self):
        with self.assertRaises(NotImplementedError):
            direct_target_position(lambda a, n: struct.pack('<I', 1), 0x40000)


if __name__ == '__main__':
    unittest.main()
