"""Offline checks of bounded schedules and independently supplied comparison data."""
import unittest
import json
import tempfile
import time
from pathlib import Path
from movement_readiness import preview_state
from movement_suite import ROOT, build_catalog, evaluate, validate
from compare_movement_cases import compare

class SuiteTests(unittest.TestCase):
    def test_timelines_are_bounded_and_neutral(self):
        catalog=build_catalog();validate(catalog)
        self.assertGreaterEqual(len(catalog['cases']),60)
        for c in catalog['cases']:
            self.assertEqual(evaluate(c['points'],c['duration']),dict(x=0.,y=0.,r2=0.))
    def test_ramp_and_release(self):
        points=[dict(t=0,x=0,y=0,r2=0),dict(t=.2,x=1,y=0,r2=0),dict(t=.3,x=1,y=0,r2=0),dict(t=.31,x=0,y=0,r2=0)]
        self.assertAlmostEqual(evaluate(points,.1)['x'],.5)
        self.assertAlmostEqual(evaluate(points,.305)['x'],.5)
    def test_disagreement_is_detected_without_false_pass(self):
        def row(t,state):return dict(t=t,state=state,matrix=[1,0,0,0,0,1,0,0,0,0,1,0,t,0,0,1])
        native=[row(0,[0,0]),row(.2,[116,0]),row(.65,[0,0])]
        preview=[row(0,[0,0]),row(.2,[3,0]),row(.65,[0,0])]
        self.assertIn('action_phase_sequence',compare(native,preview)['mismatches'])
        shifted=[row(0,[0,0]),row(.23,[116,0]),row(.7,[0,0])]
        result=compare(native,shifted)
        self.assertEqual(result['mismatches'],[])
        self.assertAlmostEqual(result['matched_sequence_timing'][1]['delta'],.03)
    def test_readiness_handles_partial_telemetry_and_active_blend(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'reports/jade/movement-suite') as folder:
            path=Path(folder)/'frames.jsonl'
            row=dict(phase='WaitingIdle',blend=dict(active=True),unix_ns=time.time_ns(),frame=10,input_strength=0.)
            path.write_text(json.dumps(row)+'\n{"partial":')
            state=preview_state(path)
            self.assertTrue(state['blend']);self.assertEqual(state['epoch'],10)
            row.update(blend=None,unix_ns=0)
            path.write_text(json.dumps(row)+'\n')
            self.assertFalse(preview_state(path)['fresh'])

if __name__=='__main__':unittest.main()
