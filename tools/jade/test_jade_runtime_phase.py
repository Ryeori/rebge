import struct
import unittest
from jade_runtime_phase import transition_phase,capture_phase_descriptor


class RuntimePhaseTests(unittest.TestCase):
    def test_descriptor_repeat_offset_is_separate_from_flags(self):
        raw=bytearray(72);raw[0]=2;raw[1]=255
        struct.pack_into('<Q',raw,40,0x12345678)
        raw[64]=3;raw[66]=60;raw[67]=12
        struct.pack_into('<H',raw,68,0x8010)
        reads=[]
        def read(address,size):
            reads.append((address,size))
            return bytes(raw[address-0x20000:address-0x20000+size])
        result=capture_phase_descriptor(read,0x20000)
        record=result['records'][1]
        self.assertEqual((record['repeat_limit'],record['speed_source_byte'],record['flags'],record['control']),
                         (3,60,12,0x8010))
        self.assertEqual(record['clip_address'],'0x12345678')
        self.assertEqual(reads,[(0x20000,8),(0x20000,72)])
        self.assertEqual(result['raw_hex'],raw.hex())

    def test_descriptor_changed_header_and_truncation_rejected(self):
        for broken in (b'\x01',b'\x02'+bytes(39)):
            calls=[]
            def read(address,size):
                calls.append(size)
                return b'\x01'+bytes(7) if len(calls)==1 else broken
            with self.assertRaises(ValueError):capture_phase_descriptor(read,0x20000)
        self.assertEqual(capture_phase_descriptor(lambda a,n: self.fail('Null dereference'),0),
                         dict(address='0x0',present=False))

    def test_transition_uses_its_own_action_and_phase(self):
        table=bytearray(40);struct.pack_into('<H',table,0,3)
        struct.pack_into('<Q',table,32,0x20000)
        descriptor=bytearray(96);descriptor[0]=2;descriptor[0x23]=0
        descriptor[32+0x23]=12;struct.pack_into('<H',descriptor,32+0x24,0x8010)
        header=bytearray(0x5c);struct.pack_into('<H',header,0x54,2);header[0x56]=1
        def read(address,size):
            block,offset=(table,address-0x10000) if address<0x20000 else (descriptor,address-0x20000)
            return bytes(block[offset:offset+size])
        phase=transition_phase(read,0x10000,header)
        self.assertEqual((phase['flags'],phase['control']),(12,0x8010))
        header[0x56]=2
        self.assertIsNone(transition_phase(read,0x10000,header)['flags'])

    def test_missing_action_does_not_dereference_descriptor(self):
        header=bytearray(0x5c);struct.pack_into('<H',header,0x54,0xffff)
        reads=[]
        def read(address,size):
            reads.append((address,size));return struct.pack('<H',3)
        self.assertIsNone(transition_phase(read,0x10000,header)['flags'])
        self.assertEqual(reads,[(0x10000,2)])


if __name__=='__main__':unittest.main()
