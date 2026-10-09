import unittest

from jade_target_hierarchy import IDENTITY,raw_affine_product
from jade_tracking_local import inverse_no_scale,compose_tracking_world,recover_tracking_local,restore_scale


class LocalTests(unittest.TestCase):
    def test_parent_rotation_translation_roundtrip(self):
        parent=[0,1,0,0,-1,0,0,0,0,0,1,0,10,20,30,1]
        local=IDENTITY.copy();local[12:15]=[2,3,4]
        world,flags=raw_affine_product(local,parent,2,6)
        restored,_=recover_tracking_local(world,flags,parent,6,[2,3,4],
            saved_scale=[1,1,1],reference_scales=([1,1,1],[0,0,0]))
        self.assertEqual(restored,local)

    def test_restore_keeps_original_translation_after_world_conversion(self):
        world=IDENTITY.copy();world[12:15]=[40,50,60]
        result,_=recover_tracking_local(world,2,IDENTITY,0,[1,2,3],
            saved_scale=[1,1,1],reference_scales=([1,1,1],[0,0,0]))
        self.assertEqual(result[12:15],[1,2,3])

    def test_scale_metadata_zero_and_unit_equivalence(self):
        for scale in ([1,1,1],[0,0,0]):
            _,flags=restore_scale(IDENTITY,14,scale,([1,1,1],[0,0,0]))
            self.assertEqual(flags,6)
        matrix,flags=restore_scale(IDENTITY,6,[2,3,4],([1,1,1],[0,0,0]))
        self.assertEqual([matrix[3],matrix[7],matrix[11]],[2,3,4])
        self.assertEqual(flags,14)
        with self.assertRaises(NotImplementedError):
            inverse_no_scale(matrix,flags)

    def test_world_composition_uses_link_flag_even_if_target_bit_clear(self):
        local=IDENTITY.copy();local[12]=2
        world=IDENTITY.copy();world[12]=10
        nodes={1:dict(flags=0x400000,parent_address=2,local_matrix=local,
                      local_flags=2,world_matrix=IDENTITY,world_flags=0),
               2:dict(flags=0,world_matrix=world,world_flags=2)}
        matrix,_=compose_tracking_world(nodes,1)
        self.assertEqual(matrix[12],12)


if __name__=='__main__':
    unittest.main()
