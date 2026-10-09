import unittest
from jade_animation_transition import advance_transition, blend_root_position


class TransitionClockTests(unittest.TestCase):
    def advance(self, **changes):
        args = dict(active=True, duration_byte=59, elapsed_u16=0, delta_seconds=0.25)
        args.update(changes)
        return advance_transition(**args)

    def test_quantized_clock_and_ratio(self):
        result = self.advance()
        self.assertEqual(result['elapsed_u16'], 3840)
        self.assertEqual(result['downstream_ratio'], 0.25)

    def test_exact_duration_does_not_overwrite_old_counter(self):
        result = self.advance(elapsed_u16=11520)
        self.assertFalse(result['active'])
        self.assertEqual(result['elapsed_u16'], 11520)
        self.assertIsNone(result['downstream_ratio'])

    def test_inactive_stale_state_is_preserved(self):
        result = self.advance(active=False, elapsed_u16=5153)
        self.assertEqual(result['elapsed_u16'], 5153)
        self.assertFalse(result['evaluate_transition'])

    def test_saved_delta_overrides_call_delta(self):
        self.assertEqual(self.advance(saved_delta_seconds=0.5)['elapsed_u16'], 7680)

    def test_fractional_counter_truncates(self):
        self.assertEqual(self.advance(delta_seconds=1/1000)['elapsed_u16'], 15)

    def test_reverse_time_rejected(self):
        with self.assertRaises(ValueError):
            self.advance(delta_seconds=-0.1)

    def test_root_position_direction_and_endpoints(self):
        old, new = [10, 20, 30], [0, 4, 8]
        self.assertEqual(blend_root_position(old, new, 0), new)
        self.assertEqual(blend_root_position(old, new, 1), old)
        self.assertEqual(blend_root_position(old, new, 0.25), [2.5, 8, 13.5])

    def test_root_position_ratio_clamps(self):
        self.assertEqual(blend_root_position([1, 2, 3], [4, 5, 6], 2), [1, 2, 3])
        self.assertEqual(blend_root_position([1, 2, 3], [4, 5, 6], -1), [4, 5, 6])


if __name__ == '__main__':
    unittest.main()
