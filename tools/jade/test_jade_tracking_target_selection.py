import unittest

from jade_tracking_target_selection import select_tracking_target as select


class TargetSelectionTests(unittest.TestCase):
    def test_self_target_keeps_offsets_on_role0_point(self):
        result = select(0x84010000, [1, 2, 3], [10, 20, 30],
                        target_enabled=True, target_is_self=True,
                        role0_position=[11, 22, 33])
        self.assertEqual(result['target'], [12, 24, 36.25])
        self.assertEqual(result['tracking_word'], 0x84000000)

    def test_other_actor_clears_offsets_for_role0_branch(self):
        result = select(0x10000, [1, 2, 3], [10, 20, 30],
                        target_enabled=True, target_is_self=False,
                        role0_position=[11, 22, 33])
        self.assertEqual(result['target'], [11, 22, 33.25])
        self.assertEqual(result['offset_after'], [0, 0, 0])

    def test_sentinel_subtraction_uses_actor_position(self):
        result = select(0x10000, [1, 2, 10001], [10, 20, 30],
                        target_enabled=True, target_is_self=True,
                        role0_position=[11, 22, 33])
        self.assertEqual(result['target'], [11, 22, 31])
        self.assertEqual(result['branch'], 'offset_z_sentinel')

    def test_zero_target_preserves_offsets_and_clears_bit16(self):
        result = select(0x84010000, [1, 2, 3], [10, 20, 30],
                        target_enabled=False, target_is_self=True)
        self.assertEqual(result['target'], [0, 0, 0])
        self.assertEqual(result['offset_after'], [1, 2, 3])
        self.assertEqual(result['tracking_word'], 0x84000000)


if __name__ == '__main__':
    unittest.main()
