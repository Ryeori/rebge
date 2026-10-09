import math
import unittest
from jade_pose_blend import blend_rotation


class PoseBlendTests(unittest.TestCase):
    def test_opposite_sign_represents_same_rotation(self):
        self.assertEqual(blend_rotation([0,0,0,1],[0,0,0,-1],0.75),[0,0,0,1])

    def test_quarter_turn_midpoint(self):
        result=blend_rotation([0,0,0,1],[0,0,1,0],0.5)
        self.assertAlmostEqual(result[2],math.sqrt(0.5),places=6)
        self.assertAlmostEqual(result[3],math.sqrt(0.5),places=6)

    def test_rotation_weight_is_not_clamped(self):
        result=blend_rotation([0,0,0,1],[0,0,1,0],2)
        self.assertAlmostEqual(result[3],-1,places=6)

    def test_near_identical_copies_first_even_at_endpoint(self):
        self.assertEqual(blend_rotation([0,0,0,1],[0.0001,0,0,1],1),[0,0,0,1])


if __name__=='__main__':unittest.main()
