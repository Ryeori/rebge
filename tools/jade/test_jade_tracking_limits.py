import unittest

from jade_tracking_limits import tracking_limits
from jade_animation_transition import f32


class LimitsTests(unittest.TestCase):
    def test_mode_zero_secondary_range(self):
        result = tracking_limits(0, secondary=True)
        self.assertEqual(result['fStack_270'], result['fStack_278'])
        self.assertEqual(result['fStack_26c'], -result['fStack_278'])
        self.assertIsNone(tracking_limits(0)['fStack_270'])

    def test_modes_have_distinct_offsets(self):
        self.assertGreater(tracking_limits(2)['fVar26'], tracking_limits(1)['fVar26'])
        self.assertGreater(tracking_limits(1)['fVar26'], tracking_limits(3)['fVar26'])
        self.assertEqual(tracking_limits(4)['fVar26'], 0)

    def test_override_then_offset_then_unrestricted(self):
        overrides = {'1421015a0': 0.2, '1421015a8': 0.3, '1421015ac': 1000}
        result = tracking_limits(0, overrides=overrides)
        self.assertEqual(result['fStack_254'], f32(f32(0.2)+f32(0.3)))
        self.assertEqual(result['fVar29'], tracking_limits(0)['fVar29'])
        result = tracking_limits(0, overrides=overrides, unrestricted=True)
        self.assertEqual(result['fStack_254'], f32(3.1415927410125732))
        self.assertEqual(result['fVar36'], -result['fStack_254'])


if __name__ == '__main__':
    unittest.main()
