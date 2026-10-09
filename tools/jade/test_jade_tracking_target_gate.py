import unittest

from jade_tracking_target_gate import tracking_target_gate as gate


class GateTests(unittest.TestCase):
    def test_blocking_clears_reference_but_phase_does_not(self):
        result=gate(0x10000,[0x10000],4)
        self.assertFalse(result['target_enabled'])
        self.assertTrue(result['clear_target_storage'])
        self.assertEqual(result['filtered_reference'],0)
        result=gate(0x10000,[],0)
        self.assertFalse(result['target_enabled'])
        self.assertFalse(result['clear_target_storage'])
        self.assertEqual(result['filtered_reference'],0x10000)

    def test_list_entries_are_not_special_reference_expanded(self):
        self.assertTrue(gate(0x10000,[1,2],12)['target_enabled'])
        self.assertFalse(gate(0,[],4)['target_enabled'])


if __name__ == '__main__':
    unittest.main()
