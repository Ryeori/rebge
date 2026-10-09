import unittest

from jade_tracking_correction import blended_angle_correction as correction
from jade_tracking_correction import tracking_corrections, continuity_allowed
from jade_tracking_limits import tracking_limits


class CorrectionTests(unittest.TestCase):
    def test_clamps_resulting_angle_not_delta(self):
        self.assertEqual(correction(2, 0.75, 1, -1, 1), 0.25)
        self.assertEqual(correction(-2, -0.75, 1, -1, 1), -0.25)

    def test_accumulation_happens_after_weight(self):
        self.assertEqual(correction(1, 0, 0.5, -2, 2, 0.25), 0.75)
        self.assertEqual(correction(1, 0, 0, -2, 2, 0.25), 0.25)

    def test_native_upper_first_with_inverted_override_range(self):
        self.assertEqual(correction(2, 0, 1, 3, 1), 1)
        self.assertEqual(correction(0, 0, 1, 3, 1), 3)

    def test_no_unrequested_wrap(self):
        self.assertEqual(correction(-3, 3, 0.5, -4, 4), -3)

    def chain(self, **changes):
        args = dict(desired_yaw=0.5, current_yaw=0, desired_pitch=0.2,
                    current_pitch=0, role1_desired=0.3, role1_current=0,
                    strength=0.5, previous_yaw=0.1,
                    limits=tracking_limits(4), allow_limit_crossing=False)
        args.update(changes)
        return tracking_corrections(**args)

    def test_continuity_rejects_opposite_direction_and_full_strength(self):
        self.assertTrue(continuity_allowed(1, 0, 0.5, 0.2))
        self.assertFalse(continuity_allowed(1, 0, 0.5, -0.2))
        self.assertFalse(continuity_allowed(1, 0, 1, 0.2))
        self.assertTrue(continuity_allowed(-1, 0, 0.5, -0.2))

    def test_crossing_bypasses_weight_even_zero(self):
        result = self.chain(desired_yaw=0.2, previous_yaw=0.3, strength=0)
        self.assertEqual(result['branch'], 'previous_crossing')
        self.assertAlmostEqual(result['role0_yaw'], 0.2)
        negative = self.chain(desired_yaw=-0.2, previous_yaw=-0.3, strength=0)
        self.assertAlmostEqual(negative['role0_yaw'], -0.2)

    def test_opposite_limit_cancels_other_roles_and_pitch(self):
        limits = tracking_limits(4, secondary=True)
        result = self.chain(current_yaw=limits['fVar29'], desired_yaw=-2,
                            limits=limits, role12_desired=0.3, role12_current=0)
        self.assertEqual(result['branch'], 'opposite_limit')
        for key in ('role0_yaw', 'role0_pitch', 'role1_yaw', 'role12_yaw'):
            self.assertEqual(result[key], 0)
        bypass = self.chain(current_yaw=limits['fVar29'], desired_yaw=-2,
                            allow_limit_crossing=True)
        self.assertNotEqual(bypass['role0_pitch'], 0)

    def test_chain_secondary_requires_its_own_initialized_limits(self):
        with self.assertRaises(ValueError):
            self.chain(role12_desired=0.2, role12_current=0)
        result = self.chain(limits=tracking_limits(4, secondary=True),
                            role12_desired=3, role12_current=0)
        self.assertEqual(result['role12_yaw'], tracking_limits(4, secondary=True)['fStack_270'])


if __name__ == '__main__':
    unittest.main()
