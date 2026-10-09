from copy import deepcopy
import unittest
from jade_tracking_window import window_input_rejections


class WindowTests(unittest.TestCase):
    def row(self):
        return dict(primary_clip_unchanged=True,tracking_inputs_unchanged=True,
                    delta_time=.016,matrices={'actor_world':'old'},brain_604_61f_hex='a')

    def test_matching_local_publications_do_not_excuse_changed_actor(self):
        before=self.row();after=deepcopy(before);after['matrices']['actor_world']='new'
        self.assertIn('actor_world:changed',window_input_rejections(before,after,after))

    def test_unstable_read_rejected_and_unchanged_window_retained(self):
        row=self.row();self.assertEqual(window_input_rejections(row,row,row),[])
        after=deepcopy(row);after['tracking_inputs_unchanged']=False
        self.assertIn('corrected:tracking_inputs_unchanged',window_input_rejections(row,after,row))


if __name__=='__main__':unittest.main()
