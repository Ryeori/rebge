import struct
import unittest
from jade_modifier24 import decode_source_record,encode_source_record,damping_weight,capture_modifier24,effective_mode_flags,lag_pose_from_position,modifier24_step,prepare_modifier24_state,finalize_modifier24_state
from jade_target_hierarchy import IDENTITY


class Modifier24Tests(unittest.TestCase):
    def test_finalizer_restores_local_parameters_but_keeps_lag(self):
        state=bytearray(256);struct.pack_into('<If',state,4,0x40a,.9)
        struct.pack_into('<6f',state,0xa8,-.1,-.1,-.1,.1,.1,.1)
        local=IDENTITY.copy();local[12]=2
        prepared=bytearray(prepare_modifier24_state(state,local,6))
        struct.pack_into('<If',prepared,4,0x1000040a,.5)
        struct.pack_into('<3f',prepared,0x88,3,4,5)
        struct.pack_into('<f',prepared,0xa8,-10)
        finalized=finalize_modifier24_state(prepared)
        self.assertEqual(finalized['local_matrix'],local)
        self.assertEqual(finalized['local_flags'],6)
        self.assertEqual(struct.unpack_from('<I',finalized['state_bytes'],4)[0],0x40a)
        self.assertEqual(struct.unpack_from('<3f',finalized['state_bytes'],0x88),(3,4,5))
        self.assertEqual(finalized['state_bytes'][8:12],state[8:12])
        self.assertEqual(finalized['state_bytes'][0xa8:0xc0],state[0xa8:0xc0])
    def test_plain_position_step_uses_prior_state(self):
        state=bytearray(256);struct.pack_into('<If',state,4,1,.5)
        nominal=IDENTITY.copy();nominal[12]=1
        quantum=struct.unpack('<f',bytes.fromhex('0e745a3b'))[0]
        result=modifier24_step(state,nominal,6,None,0,quantum)
        self.assertEqual(result['world_matrix'][12:15],[.25,0,0])
        self.assertEqual(struct.unpack_from('<3f',result['state_bytes'],0x88),(.25,0,0))
        self.assertEqual(struct.unpack_from('<f',state,0x88)[0],0)

    def test_linked_step_preserves_length_and_turns_basis(self):
        state=bytearray(256);struct.pack_into('<If',state,4,0xa,.9)
        struct.pack_into('<3f',state,0x88,0,1,0)
        nominal=IDENTITY.copy();nominal[12]=1
        result=modifier24_step(state,nominal,6,IDENTITY,0,0)
        self.assertEqual(result['effective_mode_flags'],8)
        self.assertEqual(result['world_matrix'][12:15],[0,1,0])
        for actual,expected in zip(result['world_matrix'][:3],[0,1,0]):self.assertAlmostEqual(actual,expected,places=6)

    def test_linked_constraint_clamps_before_length_restore(self):
        state=bytearray(256);struct.pack_into('<If',state,4,0x408,.9)
        nominal=IDENTITY.copy();nominal[12]=1
        struct.pack_into('<16fI',state,0xc,*nominal,6)
        struct.pack_into('<3f',state,0x88,0,1,0)
        struct.pack_into('<6f',state,0xa8,-.1,-.1,-.1,.1,.1,.1)
        result=modifier24_step(state,nominal,6,IDENTITY,0,0)
        x,y,z=result['world_matrix'][12:15]
        self.assertAlmostEqual(x*x+y*y+z*z,1,places=6)
        self.assertAlmostEqual(y/x,1/9,places=6)
    def test_linked_mode_disables_orientation_smoothing(self):
        self.assertEqual(effective_mode_flags(0x40a,True),0x408)
        self.assertEqual(effective_mode_flags(0x40a,False),0x402)

    def test_lag_direction_rotates_nominal_basis(self):
        nominal=IDENTITY.copy();nominal[12]=1
        result,_=lag_pose_from_position(nominal,6,IDENTITY,[0,1,0])
        for actual,expected in zip(result[:3],[0,1,0]):self.assertAlmostEqual(actual,expected,places=6)
        self.assertEqual(result[12:15],[0,1,0])
        with self.assertRaises(ValueError):lag_pose_from_position(nominal,6,IDENTITY,[-1,0,0])
    def test_version_zero_defaults_and_roundtrip(self):
        raw=struct.pack('<4If2I',24,0x1000000,12,0,.9,0x180,0xffffffff)
        decoded=decode_source_record(raw)
        self.assertEqual(decoded['bounds_min'],[-1,-1,-1])
        self.assertEqual(encode_source_record(decoded),raw)

    def test_version_three_fields_and_roundtrip(self):
        raw=struct.pack('<4IfI8fI',24,0x1000000,44,3,.9,0x40a,-.1,-.1,-.1,.1,.1,0,0,0,0xffffffff)
        decoded=decode_source_record(raw+b'extra GAO data')
        self.assertEqual(decoded['mode_flags'],0x40a)
        self.assertEqual(decoded['consumed_bytes'],60)
        self.assertEqual(encode_source_record(decoded),raw)
        with self.assertRaises(ValueError):decode_source_record(raw[:-1])

    def test_delta_quantization_and_zero_delta(self):
        quantum=struct.unpack('<f',bytes.fromhex('0e745a3b'))[0]
        self.assertEqual(damping_weight(.5,0),0)
        self.assertEqual(damping_weight(.5,quantum),.25)
        self.assertEqual(damping_weight(.5,quantum*2),.4375)
        with self.assertRaises(ValueError):damping_weight(.5,100)

    def test_modifier_cycle_rejected(self):
        blocks={(0x10000+0x28,8):struct.pack('<Q',0x20000),
                (0x20000+0x38,8):struct.pack('<Q',0x30000),
                (0x40000,4):struct.pack('<I',7)}
        header=bytearray(0x38);struct.pack_into('<Q',header,0,0x40000);struct.pack_into('<Q',header,0x18,0x30000)
        blocks[0x30000,0x38]=bytes(header)
        with self.assertRaises(ValueError):capture_modifier24(lambda a,n:blocks[a,n],0x10000)
