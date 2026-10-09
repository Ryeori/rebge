import unittest
from jade_rotation_channel import rotation_at_state,interpolate_channel


class RotationChannelTests(unittest.TestCase):
    def track(self,flags=128):
        return {'frames':[{'tick_raw':60,'flags':flags,'transform':{'flags':16,'quaternion_xyzw':[0,0,0,1]}},
                          {'tick_raw':0,'flags':128,'transform':{'flags':16,'quaternion_xyzw':[0,0,1,0]}}]}
    def test_exact_native_boundary_selects_next(self):
        self.assertEqual(rotation_at_state(self.track(),dict(frame_index=0,elapsed_seconds=1)),[0,0,1,0])
    def test_hold_flag_overrides_boundary(self):
        self.assertEqual(rotation_at_state(self.track(128|0x800),dict(frame_index=0,elapsed_seconds=1)),[0,0,0,1])
    def test_elapsed_uses_selected_native_segment(self):
        self.assertEqual(rotation_at_state(self.track(),dict(frame_index=1,elapsed_seconds=0)),[0,0,1,0])
    def test_negative_dot_does_not_mutate_input(self):
        second=[0,0,0,-1]
        self.assertEqual(interpolate_channel([0,0,0,1],second,.4),[0,0,0,1])
        self.assertEqual(second,[0,0,0,-1])


if __name__=='__main__':unittest.main()
