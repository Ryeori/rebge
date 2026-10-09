import math
import unittest
from copy import deepcopy
from jade_target_hierarchy import IDENTITY
from jade_tracking_limits import tracking_limits
from jade_tracking_step import tracking_step


class TrackingStepTests(unittest.TestCase):
    def evaluate(self,**kwargs):
        nodes={100:dict(flags=0,world_matrix=IDENTITY.copy(),world_flags=0)}
        previous={100:(IDENTITY.copy(),0)}
        for address in (1,2,3):
            local=IDENTITY.copy();local[14]=float(address)
            nodes[address]=dict(flags=0x400001,parent_address=100,
                local_matrix=local,local_flags=2,world_matrix=local,world_flags=2)
            previous[address]=(local.copy(),2)
        original=deepcopy(nodes)
        result=tracking_step(nodes,100,{0:1,1:2,12:3},previous,100,
            strength=1,limits=tracking_limits(0,secondary=True),sign_axis=[0,0,1],
            allow_limit_crossing=True,scale_references=([1,1,1],[0,0,0]),
            coefficients=lambda a:(math.cos(a),math.sin(a)),**kwargs)
        self.assertEqual(nodes,original)
        for address in (1,2,3):
            self.assertEqual(result['nodes'][address]['local_matrix'][12:15],original[address]['local_matrix'][12:15])
        return result
    def test_target_turn_distributes_yaw(self):
        result=self.evaluate(target=[1,-2,1])
        self.assertEqual(result['desired']['branch'],'resolved_target')
        yaw=result['desired']['yaw']
        self.assertAlmostEqual(result['scalar_corrections']['role1_yaw'],yaw/3,places=6)
        self.assertAlmostEqual(result['scalar_corrections']['role12_yaw'],yaw/5,places=6)
    def test_phase_blocked_uses_rebuilt_pose(self):
        result=self.evaluate(target=[1,-2,1],phase_blocked=True)
        self.assertEqual(result['desired']['branch'],'rebuilt_forward')
        self.assertEqual(result['scalar_corrections']['role0_yaw'],0)
    def test_behind_target_falls_back(self):
        result=self.evaluate(target=[0,2,1])
        self.assertEqual(result['desired']['branch'],'target_outside_yaw_fallback')


if __name__=='__main__':unittest.main()
