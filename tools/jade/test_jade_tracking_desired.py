import unittest
from jade_pose import rotation_matrix
from jade_tracking_limits import tracking_limits
from jade_tracking_desired import role0_desired,secondary_desired


class DesiredTrackingTests(unittest.TestCase):
    def evaluate(self,target,**kwargs):
        return role0_desired([0,-1,0],rotation_matrix([0,0,0,1]),target,
            phase_blocked=kwargs.get('blocked',False),reject_outside_yaw=kwargs.get('reject',True),
            limits=tracking_limits(kwargs.get('mode',0)),sign_axis=[0,0,1])
    def test_forward_target(self):
        result=self.evaluate([0,-10,0])
        self.assertEqual(result['branch'],'resolved_target')
        self.assertEqual(result['yaw'],0)
    def test_target_behind_falls_back(self):
        self.assertEqual(self.evaluate([0,10,0])['branch'],'target_outside_yaw_fallback')
    def test_unrestricted_target_reaches_behind(self):
        self.assertEqual(self.evaluate([0,10,0],reject=False)['branch'],'resolved_target')
    def test_pitch_offset_only_applies_target_branch(self):
        self.assertGreater(self.evaluate([0,-10,0],mode=1)['pitch'],0)
        self.assertEqual(self.evaluate([0,-10,0],mode=1,blocked=True)['pitch'],0)
    def test_target_yaw_distribution(self):
        result=secondary_desired(dict(branch='resolved_target',yaw=1.5),0.2,0.1)
        self.assertEqual(result['role1_yaw'],0.5)
        self.assertAlmostEqual(result['role12_yaw'],0.3,places=6)
    def test_parameter7_precedes_parameter8(self):
        result=secondary_desired(dict(branch='resolved_target',yaw=1.5),0.2,
                                 parameter7=True,parameter8=True)
        self.assertEqual(result['role1_yaw'],1.5)
    def test_fallback_keeps_secondary_rebuilt_angles(self):
        result=secondary_desired(dict(branch='rebuilt_forward',yaw=1.5),0.2,0.1)
        self.assertAlmostEqual(result['role1_yaw'],0.2,places=6)
        self.assertEqual(result['role12_yaw'],0.1)
    def test_parameter8_preserves_prior_yaw_instead_of_rebuilt(self):
        result=secondary_desired(dict(branch='resolved_target',yaw=1.5),0.2,
            parameter8=True,current_role1_yaw=-0.4)
        self.assertAlmostEqual(result['role1_yaw'],-0.4,places=6)
        with self.assertRaises(ValueError):
            secondary_desired(dict(branch='resolved_target',yaw=1.5),0.2,parameter8=True)


if __name__=='__main__':unittest.main()
