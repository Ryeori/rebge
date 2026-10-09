import struct
import unittest
from jade_clip_consistency import check_clip_prefix


class ClipConsistencyTests(unittest.TestCase):
    def memory(self):
        return {(100,16):struct.pack('<QQ',200,300),
                (200,16):struct.pack('<QHHI',400,2,0,0),
                (300,24):bytes(24)}
    def test_second_track_change_detected_with_first_track_unchanged(self):
        original=self.memory();live=dict(original)
        live[300,24]=bytes(12)+struct.pack('<f',1)+bytes(8)
        result=check_clip_prefix(lambda a,n:live[a,n],100,original)
        self.assertFalse(result['states_unchanged'])
        self.assertTrue(result['link_unchanged'])
    def test_resource_switch_detected(self):
        original=self.memory();live=dict(original)
        live[100,16]=struct.pack('<QQ',999,300)
        self.assertFalse(check_clip_prefix(lambda a,n:live[a,n],100,original)['link_unchanged'])
    def test_unchanged_prefix(self):
        original=self.memory()
        result=check_clip_prefix(lambda a,n:original[a,n],100,original)
        self.assertTrue(all(result[k] for k in ('states_unchanged','link_unchanged','resource_unchanged')))


if __name__=='__main__':unittest.main()
