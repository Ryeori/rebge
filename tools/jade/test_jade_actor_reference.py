import unittest
from jade_target_hierarchy import IDENTITY
from jade_actor_reference import actor_reference_position,refresh_reference


class ActorReferenceTests(unittest.TestCase):
    def test_relative_translation_and_height(self):
        actor=IDENTITY.copy();actor[12]=10
        reference=IDENTITY.copy();reference[12]=12
        self.assertEqual(actor_reference_position([1,2,3],reference,2,actor,2,height=.5,add_height=True),[3,2,3.5])
    def test_scale_rejected(self):
        with self.assertRaises(NotImplementedError):
            actor_reference_position([1,2,3],IDENTITY,8,IDENTITY,0)

    def test_refresh_rotated_actor_uses_actor_times_inverse_root(self):
        actor=IDENTITY.copy();actor[:3]=[0,1,0];actor[4:7]=[-1,0,0];actor[12:15]=[10,20,30]
        root=IDENTITY.copy();root[12:15]=[2,3,4]
        ref,flags=refresh_reference(root,2,actor,6)
        self.assertEqual(ref[12:15],[13,18,26])
        self.assertEqual(actor_reference_position([2,3,4],ref,flags,actor,6),[0,0,0])

    def test_refresh_rejects_scaled_actor(self):
        with self.assertRaises(NotImplementedError):
            refresh_reference(IDENTITY,0,IDENTITY,8)


if __name__=='__main__':unittest.main()
