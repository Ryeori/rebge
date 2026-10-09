import math
import unittest

from jade_tracking_angles import yaw_difference


class YawTests(unittest.TestCase):
    def test_axis_sign_and_argument_order(self):
        self.assertAlmostEqual(yaw_difference([1, 0, 9], [0, 1, -9], [0, 0, 1]), math.pi/2, places=6)
        self.assertAlmostEqual(yaw_difference([0, 1, 0], [1, 0, 0], [0, 0, 1]), -math.pi/2, places=6)
        self.assertAlmostEqual(yaw_difference([1, 0, 0], [0, 1, 0], [0, 0, -1]), -math.pi/2, places=6)

    def test_parallel_antiparallel(self):
        self.assertEqual(yaw_difference([2, 0, 0], [3, 0, 0], [0, 0, 1]), 0)
        self.assertAlmostEqual(yaw_difference([1, 0, 0], [-1, 0, 0], [0, 0, 1]), math.pi, places=6)

    def test_vertical_projection_rejected(self):
        with self.assertRaises(ValueError):
            yaw_difference([0, 0, 1], [1, 0, 0], [0, 0, 1])


if __name__ == '__main__':
    unittest.main()
