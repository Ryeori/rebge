import unittest

from jade_tracking_phase import tracking_phase_gate as gate


class PhaseTests(unittest.TestCase):
    def test_allowed_resets_counter(self):
        self.assertEqual(gate(9, 1, 0, current_flags=4)['counter'], 0)

    def test_missing_current_phase_resets(self):
        self.assertTrue(gate(9, 1, 0)['continue'])

    def test_transition_missing_skips_block(self):
        self.assertEqual(gate(9, 1, 0, current_flags=0,
                              component_high_byte=3)['counter'], 0)
        self.assertFalse(gate(9, 1, 0, current_flags=4,
                              component_high_byte=3, transition_flags=0)['continue'])

    def test_six_call_boundary(self):
        self.assertTrue(gate(4, 1, 0, current_flags=0)['continue'])
        result = gate(5, 1, 0, current_flags=0)
        self.assertEqual(result['counter'], 6)
        self.assertFalse(result['continue'])

    def test_control_freezes_counter(self):
        self.assertEqual(gate(3, 1, 0, current_flags=0,
                              phase_control=0x1000)['counter'], 3)

    def test_time_ramp_boundary_and_byte_wrap(self):
        result = gate(15, 1, 1/60, current_flags=0, phase_control=0x8000)
        self.assertEqual(result, {'counter': 16, 'strength': 1.0, 'continue': False})
        result = gate(1, 1, 256/60, current_flags=0, phase_control=0x8000)
        self.assertEqual(result['counter'], 1)
        self.assertTrue(result['continue'])


if __name__ == '__main__':
    unittest.main()
