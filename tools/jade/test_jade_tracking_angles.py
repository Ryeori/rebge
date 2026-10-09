import math
import unittest
from jade_tracking_angles import pitch_difference
from jade_animation_transition import f32


class PitchTests(unittest.TestCase):
    def test_horizontal_yaw_does_not_change_pitch(self):
        self.assertEqual(pitch_difference([1,0,0],[0,1,0]),0)

    def test_native_projected_normalization_avoids_false_horizontal_pitch(self):
        # Rounded reciprocal/multiply in 1400369e0 reaches dot=1 here;
        # double hypot/division instead creates an artificial .0003453 pitch.
        diagonal=f32(math.sqrt(0.5))
        self.assertEqual(pitch_difference([1,0,0],[diagonal,diagonal,0]),0)

    def test_elevation_sign(self):
        diagonal=math.sqrt(0.5)
        self.assertAlmostEqual(pitch_difference([diagonal,0,diagonal],[1,0,0]),math.pi/4,places=6)
        self.assertAlmostEqual(pitch_difference([diagonal,0,-diagonal],[1,0,0]),-math.pi/4,places=6)

    def test_degenerate_and_nonunit_rejected(self):
        for vector in ([0,0,1],[2,0,0]):
            with self.assertRaises(ValueError):pitch_difference(vector,[1,0,0])


if __name__=='__main__':unittest.main()
