import unittest
from jade_translation_channel import translation_at_state


class TranslationChannelTests(unittest.TestCase):
    def track(self,points):
        return {'frames':[{'tick_raw':60,'flags':128,'transform':{'flags':len(points),'float3_channels':points}},
                          {'tick_raw':0,'flags':128,'transform':{'flags':1,'float3_channels':[[1,0,0]]}}]}
    def test_linear_quadratic_cubic_midpoint(self):
        for points,expected in [([[0,0,0]],.5),([[0,0,0],[0,0,0]],.25),
                                ([[0,0,0],[0,0,0],[0,0,0]],.125)]:
            self.assertEqual(translation_at_state(self.track(points),dict(frame_index=0,elapsed_seconds=.5))[0],expected)
    def test_boundary_selects_next(self):
        self.assertEqual(translation_at_state(self.track([[0,0,0]]),dict(frame_index=0,elapsed_seconds=1)),[1,0,0])


if __name__=='__main__':unittest.main()
