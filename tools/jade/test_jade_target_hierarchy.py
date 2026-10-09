import unittest

from jade_target_hierarchy import IDENTITY, raw_affine_product, linked_target_position


class HierarchyTests(unittest.TestCase):
    def test_rotation_and_translation_order(self):
        parent = [0,1,0,0,-1,0,0,0,0,0,1,0,10,20,30,1]
        local = IDENTITY.copy();local[12:15] = [2,3,4]
        result, flags = raw_affine_product(local, parent, 2, 6)
        self.assertEqual(result[12:15], [7,22,34])
        self.assertEqual(flags, 6)

    def test_raw_fields_consumed_even_with_clear_flags(self):
        local = IDENTITY.copy();local[12] = 3
        result, flags = raw_affine_product(local, IDENTITY, 0, 0)
        self.assertEqual(result[12], 3)
        self.assertEqual(flags, 2)
        with self.assertRaises(NotImplementedError):
            raw_affine_product(local, IDENTITY, 8, 0)

    def nodes(self):
        world = IDENTITY.copy();world[12] = 10
        local = IDENTITY.copy();local[12] = 2
        return {1: dict(flags=0x400001,parent_address=2,local_matrix=local,
                        local_flags=2,world_matrix=world,world_flags=2),
                2: dict(flags=0,world_matrix=world,world_flags=2)}

    def test_linked_local_chain_ignores_stale_child_world(self):
        self.assertEqual(linked_target_position(self.nodes(), 1)['position'], [12,0,0])

    def test_missing_parent_fallback_returns_original_world(self):
        nodes = self.nodes();nodes[1]['parent_address'] = 0
        result = linked_target_position(nodes, 1)
        self.assertEqual(result['position'], [10,0,0])
        self.assertEqual(result['branch'], 'missing_parent_fallback')

    def test_cycles_and_missing_nodes_rejected(self):
        nodes = self.nodes();nodes[1]['parent_address'] = 1
        with self.assertRaises(ValueError):
            linked_target_position(nodes, 1)
        nodes[1]['parent_address'] = 3
        with self.assertRaises(ValueError):
            linked_target_position(nodes, 1)


if __name__ == '__main__':
    unittest.main()
