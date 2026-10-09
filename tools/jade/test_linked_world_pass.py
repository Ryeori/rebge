import unittest
from jade_target_hierarchy import IDENTITY
from jade_linked_world_pass import linked_world_pass


def node(parent,position,marker=0):
    local=IDENTITY.copy();local[12]=position
    return dict(flags=0x400000 if parent else 0,parent_address=parent,
        visitation_byte_33=marker,world_matrix=IDENTITY.copy(),world_flags=0,
        local_matrix=local,local_flags=2)


class LinkedWorldPassTests(unittest.TestCase):
    def test_child_before_parent_updates_ancestor_first(self):
        nodes={4:node(0,0),8:node(4,2),12:node(8,3)}
        nodes[4]['world_matrix'][12]=10
        result=linked_world_pass(nodes,[12,8],0)
        self.assertEqual(result['writes'],[8,12])
        self.assertEqual(result['nodes'][12]['world_matrix'][12],15)
        self.assertEqual(nodes[12]['world_matrix'][12],0)

    def test_second_pass_uses_new_locals_and_preserves_marker_low_bits(self):
        nodes={4:node(0,0,7),8:node(4,2,13)}
        first=linked_world_pass(nodes,[8],0)
        first['nodes'][8]['local_matrix'][12]=5
        self.assertEqual(first['nodes'][8]['world_matrix'][12],2)
        second=linked_world_pass(first['nodes'],[8],1)
        self.assertEqual(second['nodes'][8]['world_matrix'][12],5)
        self.assertEqual(second['nodes'][8]['visitation_byte_33'],13)

    def test_tagged_entries_skipped_and_counter_wraps(self):
        result=linked_world_pass({},[0,5],0xffffffff)
        self.assertEqual(result['next_pass_counter'],0)
        self.assertEqual(result['writes'],[])

    def test_cycle_rejected(self):
        with self.assertRaises(ValueError):
            linked_world_pass({4:node(8,1),8:node(4,1)},[4],0)


if __name__=='__main__':unittest.main()
