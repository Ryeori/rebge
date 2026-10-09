import unittest
from copy import deepcopy
from jade_trace_consistency import PRIMARY_CHECKS,rejection_reasons,pair_candidate


class TraceConsistencyTests(unittest.TestCase):
    def sample(self):
        return dict({k:True for k in PRIMARY_CHECKS},component_flags_u16=0x101,
            actor={'address':'0x1000'},update_pass_before=10,update_pass_after=10,
            target_resolved_address='0x1000')
    def test_old_missing_checks_rejected(self):
        sample=self.sample();del sample['brain_unchanged']
        self.assertIn('brain_unchanged:missing',rejection_reasons(sample))
    def test_active_transition_requires_checks(self):
        sample=self.sample();sample['component_flags_u16']=0x301
        self.assertIn('transition_states_unchanged',rejection_reasons(sample))
    def test_pass_wrap_candidate_is_not_native_proof(self):
        first=self.sample();first['update_pass_after']=0xffffffff
        second=deepcopy(first);second['update_pass_before']=0
        result=pair_candidate(first,second)
        self.assertTrue(result['candidate']);self.assertFalse(result['native_prior_input_proven'])
    def test_skipped_passes_rejected(self):
        first=self.sample();second=self.sample();second['update_pass_before']=12
        self.assertFalse(pair_candidate(first,second)['candidate'])
    def test_matrix_write_with_unchanged_pass_and_clip_is_rejected(self):
        sample=self.sample();sample['pose_matrices_unchanged']=False
        self.assertIn('pose_matrices_unchanged:changed',rejection_reasons(sample))
    def test_changed_controller_inputs_rejected_despite_stable_pass(self):
        for check in ('primary_phase_descriptor_unchanged','actor_dispatch_prefix_unchanged',
                      'reference_entry_manager_unchanged'):
            sample=self.sample();sample[check]=False
            self.assertIn(check+':changed',rejection_reasons(sample))


if __name__=='__main__':unittest.main()
