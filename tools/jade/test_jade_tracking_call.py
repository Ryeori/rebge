import unittest

from jade_tracking_call import tracking_arguments


class TrackingCallTests(unittest.TestCase):
    def pack(self, base=0, word=0, strength=1.0, enabled=True):
        return tracking_arguments(base, word, strength, 0.5, 2.0,
                                  target_enabled=enabled)

    def test_windows_stack_parameter_order(self):
        args = self.pack(word=0xfc000003)
        self.assertEqual(args['mode'], 3)
        for index, bit in enumerate((31, 30, 29, 28, 27, 26), 5):
            self.assertEqual(args[f'parameter_{index}'], 1 << bit)

    def test_addition_carries_into_mask_and_wraps(self):
        args = self.pack(base=1, word=0x03ffffff)
        self.assertEqual(args['mode'], 0)
        self.assertEqual(args['parameter_10'], 0x04000000)
        self.assertEqual(self.pack(base=1, word=0xffffffff)['parameter_5'], 0)

    def test_zero_target_clears_bit_before_addition(self):
        self.assertEqual(self.pack(word=0x10002, enabled=False)['mode'], 2)
        self.assertEqual(self.pack(word=0x10002)['mode'], 0x10002)

    def test_strength_scaling_and_clamp(self):
        args = tracking_arguments(0, 0, 0.5, 0.25, 2,
                                  target_enabled=True)
        self.assertEqual(args['strength'], 0.25)
        self.assertEqual(self.pack(strength=2)['strength'], 1)
        self.assertEqual(self.pack(strength=-2)['strength'], 0)

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            self.pack(strength=float('nan'))


if __name__ == '__main__':
    unittest.main()
