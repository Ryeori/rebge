import unittest

from probe_runtime_sampled_pose import select_runtime_tracks


class InstanceTests(unittest.TestCase):
    def test_transition_uses_its_own_frame_state(self):
        tracks=[{'indexed_slot':9,'frame_headers':[{'tick_raw':3,'flags':16}],
                 'frame_index':2,'elapsed_seconds':0.05}]
        snapshot={'animation_state':{'instances':{
            'primary':{'clip_link':{'tracks':[]}},
            'transition':{'clip_link':{'tracks':tracks}}}}}
        source={'tracks':[{'short1':9,'frames':[{'tick_raw':3,'flags':16}]}]}
        self.assertIs(select_runtime_tracks(snapshot,source,'transition'),tracks)
        with self.assertRaises(ValueError):
            select_runtime_tracks(snapshot,source,'primary')

    def test_equal_count_with_different_headers_rejected(self):
        snapshot={'animation_state':{'instances':{'primary':{'clip_link':{
            'tracks':[{'indexed_slot':9,'frame_headers':[{'tick_raw':4,'flags':16}]}]}}}}}
        source={'tracks':[{'short1':9,'frames':[{'tick_raw':3,'flags':16}]}]}
        with self.assertRaises(ValueError):
            select_runtime_tracks(snapshot,source,'primary')


if __name__=='__main__':
    unittest.main()
