import unittest
from audit_tracking_trace import INPUT_CHECKS,input_rejection_reasons


class TrackingInputAuditTests(unittest.TestCase):
    def test_missing_checks_are_rejected(self):
        self.assertEqual(input_rejection_reasons({}),[key+':missing' for key in INPUT_CHECKS])

    def test_changed_reference_not_promoted_by_present_payload(self):
        sample={key:True for key in INPUT_CHECKS}
        sample.update(actor_reference_matrix_hex='00',actor_reference_unchanged=False)
        self.assertEqual(input_rejection_reasons(sample),['actor_reference_unchanged:changed'])

    def test_stable_checks_accepted(self):
        self.assertEqual(input_rejection_reasons({key:True for key in INPUT_CHECKS}),[])
