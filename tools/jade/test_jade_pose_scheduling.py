import unittest
from jade_pose_scheduling import local_callback_candidate,palette_initial_callback


class PoseSchedulingTests(unittest.TestCase):
    def test_disabled_actor_skips_local_callback(self):
        self.assertFalse(local_callback_candidate(0x1000,2,4,True))
        self.assertTrue(local_callback_candidate(0x1000,2,0,True))
    def test_tagged_pointer_and_missing_indexed_list_skip(self):
        self.assertFalse(local_callback_candidate(0x1001,2,0,True))
        self.assertFalse(local_callback_candidate(0x1000,2,0,False))
    def test_active_component_publishes_without_initial_callback(self):
        self.assertFalse(palette_initial_callback(0x101,True))
        self.assertTrue(palette_initial_callback(0x100,True))
        self.assertFalse(palette_initial_callback(0,False))


if __name__=='__main__':unittest.main()
