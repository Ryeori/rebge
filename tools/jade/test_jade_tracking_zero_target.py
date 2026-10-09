import math
import unittest

from jade_target_hierarchy import IDENTITY
from jade_tracking_limits import tracking_limits
from jade_tracking_rotation import rotate_world_xy
from jade_tracking_zero_target import zero_target_step


class ZeroTargetTests(unittest.TestCase):
    def run_step(self,strength=1,angle=0.2):
        nodes={100:dict(flags=0,world_matrix=IDENTITY.copy(),world_flags=0)}
        prior={100:(IDENTITY.copy(),0)}
        for address in (1,2,3):
            local=IDENTITY.copy();local[12]=address
            nodes[address]=dict(flags=0x400001,parent_address=100,
                local_matrix=local,local_flags=2,world_matrix=local,world_flags=2)
            rotated,flags=rotate_world_xy(local,2,math.cos(angle),math.sin(angle))
            prior[address]=(rotated,flags)
        result=zero_target_step(nodes,100,{0:1,1:2,12:3},prior,100,
            strength=strength,limits=tracking_limits(0,secondary=True),sign_axis=[0,0,1],
            allow_limit_crossing=True,scale_references=([1,1,1],[0,0,0]),
            coefficients=lambda a:(math.cos(a),math.sin(a)))
        return nodes,result

    def test_full_strength_recovers_desired_basis_and_preserves_positions(self):
        original,result=self.run_step()
        for address in (1,2,3):
            matrix=result['nodes'][address]['local_matrix']
            for index in (0,1,2,4,5,6,8,9,10):
                self.assertAlmostEqual(matrix[index],IDENTITY[index],places=5)
            self.assertEqual(matrix[12:15],original[address]['local_matrix'][12:15])
        self.assertNotEqual(result['scalar_corrections']['role0_yaw'],0)

    def test_zero_strength_retains_previous_yaw_without_mutating_inputs(self):
        original,result=self.run_step(strength=0)
        self.assertEqual(result['scalar_corrections']['role0_yaw'],0)
        self.assertGreater(abs(result['nodes'][1]['local_matrix'][1]),0.1)
        self.assertEqual(original[1]['local_matrix'][1],0)


if __name__=='__main__':
    unittest.main()
