import unittest
from split_tracking_order_clips import clip_runs


class ClipRunTests(unittest.TestCase):
    def record(self):
        return dict(actor_component_unchanged=True,primary_resource_address='a',
                    primary_clip={'tracks':[{}]},clip_catalog={'a':{'tracks':[{}]},'b':{'tracks':[{},{}]}},
                    rows=[{'primary_resource_address':key,'primary_states_hex':'00'*(12 if key=='a' else 24)}
                          for key in ('a','a','b','a')],limitations=[])

    def test_returned_clip_remains_separate_and_state_counts_follow_clip(self):
        record=self.record();runs=clip_runs(record)
        self.assertEqual([len(r['rows']) for r in runs],[2,1,1])
        self.assertEqual([r['primary_track_count'] for r in runs],[1,2,1])
        self.assertEqual(runs[-1]['rows'][0]['source_observation_index'],3)
        self.assertNotIn('source_observation_index',record['rows'][3])

    def test_mixed_metadata_and_changed_actor_rejected(self):
        record=self.record();record['rows'][2]['primary_states_hex']='00'*12
        with self.assertRaises(ValueError):clip_runs(record)
        record=self.record();record['actor_component_unchanged']=False
        with self.assertRaises(ValueError):clip_runs(record)


if __name__=='__main__':unittest.main()
