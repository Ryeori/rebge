import math
import struct
import unittest
from jade_animation import decode_animation, encode_animation
from jade_pose import rotation_matrix, rotation_samples, translation_sample, interpolate_translation, validate_link_graph, affine_product, assemble_rest_pose
from jade_animation_time import locate_transform_segment
from jade_pose import interpolate_rotation
from jade_animation_sample import sample_local_track, clone_parent_mapping
from jade_animation_sample import sample_clone_local_matrices
from jade_animation_root import reference_matrix_offset, convert_root_channels
from jade_animation_root import rigid_inverse, refresh_root_reference
from jade_animation_root import translation_reference_gate
from jade_clone_pose import assemble_attached_clone_base_world
from jade_clone_pose import initialize_source_clones, assemble_sampled_clone_world
from probe_sally_control_tracks import decode_event_records
from jade_vm_link import link_record
from jade_vm_state import VMState, UnsupportedVM
from jade_resource_instance import select_actor_resource, clamp_instance_parameter


class AnimationTests(unittest.TestCase):
    def test_actor_resource_index_indirection_and_parameter_clamp(self):
        actor = {'flags': 0x8000000, 'resource_indices': [8, 3]}
        self.assertEqual(select_actor_resource(actor, 1, enabled=True, resource_count=10), 3)
        self.assertEqual(select_actor_resource(actor, 2, enabled=True, resource_count=10), -1)
        self.assertEqual(select_actor_resource(actor, 0, enabled=False, resource_count=10), -1)
        self.assertEqual(clamp_instance_parameter(-1), 0)
        self.assertEqual(clamp_instance_parameter(2), 1)
        self.assertEqual(clamp_instance_parameter(.5), .5)

    def test_component_mask_updates_previous_context_and_restores_default(self):
        objects = {'actor': {'flags_u16_50': 0xF0}}
        state = VMState(context_sentinel=0, objects=objects, default_actor='default')
        state.object_context = 'actor'
        state.stack = [{'type': 1, 'value': 3}, {'type': 1, 'value': 0x30}]
        state.execute({'runtime_category': 2, 'runtime_selector': 248})
        self.assertEqual(objects['actor']['flags_u16_50'], 0xC3)
        self.assertEqual(state.object_context, 'default')
        self.assertEqual(state.stack, [])

    def test_vm_vector_constructor_order_and_mixed_scalar_types(self):
        state = VMState(context_sentinel=0, objects={})
        state.stack = [{'type': 1, 'value': 3}, {'type': 2, 'value': 2.5}, {'type': 1, 'value': -1}]
        state.execute({'runtime_category': 2, 'runtime_selector': 16})
        self.assertEqual(state.stack, [{'type': 3, 'value': [3., 2.5, -1.]}])
        before = list(state.stack)
        with self.assertRaises(ValueError):
            state.execute({'runtime_category': 2, 'runtime_selector': 16})
        self.assertEqual(state.stack, before)

    def test_vm_literal_preserves_float_bits_and_context(self):
        state = VMState(context_sentinel=0, objects={})
        state.execute({'runtime_category': 0, 'runtime_selector': 2,
                       'value_i32': 0x3F800000})
        self.assertEqual(state.stack[-1], {'type': 2, 'value': 1.0})
        state.execute({'runtime_category': 0, 'runtime_selector': 6,
                       'value_i32': 0, 'resolved_reference_u64': 0})
        state.execute({'runtime_category': 1, 'runtime_selector': 6})
        self.assertEqual(state.object_context, 0)
        self.assertEqual(len(state.stack), 1)
        before = list(state.stack)
        with self.assertRaises(UnsupportedVM):
            state.execute({'runtime_category': 2, 'runtime_selector': 9999})
        self.assertEqual(state.stack, before)
        self.assertFalse(state.execute({'terminal': True}))

    def test_reference_literal_null_and_sentinels(self):
        record = {'dispatch_u8': 1, 'selector_u16': 40, 'value_i32': 0, 'metadata_u8': 0}
        self.assertEqual(link_record(record, {1: 0}, {40: 6})['resolved_reference_u64'], 0)
        record['value_i32'] = 2
        self.assertEqual(link_record(record, {1: 0}, {40: 6})['resolved_reference_u64'], 2)
        record['value_i32'] = 123
        self.assertIn('unresolved', link_record(record, {1: 0}, {40: 6}))

    def test_source_vm_categories_require_linking(self):
        record = {'dispatch_u8': 1, 'selector_u16': 34, 'value_i32': 0, 'metadata_u8': 0}
        linked = link_record(record, {1: 0, 2: 1, 3: 2}, {34: 2, 2054: 6})
        self.assertEqual((linked['runtime_category'], linked['runtime_selector']), (0, 2))
        record.update(dispatch_u8=2, selector_u16=2054)
        linked = link_record(record, {1: 0, 2: 1, 3: 2}, {34: 2, 2054: 6})
        self.assertEqual((linked['runtime_category'], linked['runtime_selector']), (1, 6))
        record['dispatch_u8'] = 31
        self.assertTrue(link_record(record, {}, {})['terminal'])

    def test_native_event_record_signed_value_and_dispatch(self):
        raw = struct.pack('<iHBB', -7, 0x806, 0, 2)
        self.assertEqual(decode_event_records(raw), [{'value_i32': -7,
            'selector_u16': 0x806, 'metadata_u8': 0, 'dispatch_u8': 2}])
        with self.assertRaises(ValueError):
            decode_event_records(raw[:-1])

    def test_attachment_precedes_animation(self):
        base = rotation_matrix([0, 0, 0, 1]); base[12] = 10
        objects = [{'key': 'a', 'flags': '00010000', 'gao_matrix': base}]
        clones = initialize_source_clones(objects)
        track = {'index': 0, 'short1': 0, 'frames': [
            {'flags': 128, 'tick_raw': 0, 'transform': {'flags': 1,
             'float3_channels': [[2, 0, 0]]}}]}
        identity = rotation_matrix([0, 0, 0, 1])
        context = {'actor_matrix': identity, 'reference_matrix': identity,
                   'reference_flags': 0, 'translation_gates': {0: False}}
        snapshot = sample_clone_local_matrices({'tracks': [track]}, clones, 0, root_context=context)
        self.assertEqual(assemble_sampled_clone_world(snapshot)['a'][12], 2)
        self.assertEqual(objects[0]['gao_matrix'][12], 10)

    def test_runtime_translation_gate_actor_and_scan_boundary(self):
        tracks = [{'actor': None, 'current_frame_flags': 0x84},
                  {'actor': 'other', 'current_frame_flags': 0x84},
                  {'actor': 'hero', 'current_frame_flags': 0x80}]
        self.assertTrue(translation_reference_gate(tracks, 2, 'hero', 'hero'))
        self.assertFalse(translation_reference_gate(tracks, 0, 'other', 'hero'))
        self.assertTrue(translation_reference_gate(tracks, 1, 'other', 'hero'))
        tracks[0]['current_frame_flags'] = 0x44
        self.assertFalse(translation_reference_gate(tracks, 2, 'hero', 'hero'))

    def test_attached_clone_base_pose_requires_extra_matrix(self):
        actor = rotation_matrix([0, 0, math.sqrt(.5), math.sqrt(.5)])
        actor[12:15] = [10, 0, 0]
        root = rotation_matrix([0, 0, 0, 1]); root[12] = 2
        child = rotation_matrix([0, 0, 0, 1]); child[12] = 3
        snapshot = {'actor_destination_matrix': actor, 'objects': [
            {'key': 'a', 'clone_parent': None, 'jade_destination_matrix': child},
            {'key': 'b', 'clone_parent': 'a', 'jade_destination_matrix': child}]}
        with self.assertRaises(ValueError):
            assemble_attached_clone_base_world(snapshot, {})
        world = assemble_attached_clone_base_world(snapshot, {'a': root})
        self.assertAlmostEqual(world['a'][13], 2)
        self.assertAlmostEqual(world['b'][13], 5)

    def test_explicit_root_context_integration(self):
        track = {'index': 0, 'short1': 65535, 'frames': [
            {'flags': 128, 'tick_raw': 0, 'transform': {'flags': 1,
             'float3_channels': [[2, 0, 0]]}}]}
        reference = rotation_matrix([0, 0, 0, 1])
        reference[12:15] = [10, 20, 30]
        context = {'actor_matrix': rotation_matrix([0, 0, 0, 1]),
                   'reference_matrix': reference, 'reference_flags': 2,
                   'translation_gates': {0: True}}
        result = sample_clone_local_matrices({'tracks': [track]}, [], 0, root_context=context)
        self.assertEqual(result['actor_destination_matrix'][12:15], [12, 20, 30])
        self.assertTrue(result['complete_local_snapshot'])
        self.assertEqual(context['actor_matrix'][12:15], [0, 0, 0])

    def test_root_reference_refresh_noncommuting_transforms(self):
        root = rotation_matrix([0, 0, math.sqrt(.5), math.sqrt(.5)])
        root[12:15] = [2, 3, 4]
        actor = rotation_matrix([math.sqrt(.5), 0, 0, math.sqrt(.5)])
        actor[12:15] = [10, 20, 30]
        reference = refresh_root_reference(actor, root, root_flags=6)
        restored = affine_product(root, reference)
        for a, b in zip(restored, actor):
            self.assertAlmostEqual(a, b)
        root[0] *= 2
        root[1] *= 2
        with self.assertRaises(ValueError):
            rigid_inverse(root)
        with self.assertRaises(ValueError):
            refresh_root_reference(actor, actor, root_flags=8)

    def test_runtime_root_reference_selection(self):
        self.assertIsNone(reference_matrix_offset(0))
        self.assertEqual(reference_matrix_offset(0x4000000), 0x44)
        self.assertEqual(reference_matrix_offset(0x4010000), 0x88)

    def test_root_reference_rotation_and_conditional_position(self):
        reference = rotation_matrix([0, 0, math.sqrt(.5), math.sqrt(.5)])
        reference[12:15] = [10, 20, 30]
        sample = {'slot': 65535, 'track_index': 0,
                  'quaternion_xyzw': [0, 0, 0, 1], 'position_xyz': [2, 0, 0]}
        converted = convert_root_channels(sample, reference, reference_flags=4,
                                          translation_reference_enabled=True)
        self.assertAlmostEqual(converted['position_xyz'][0], 10)
        self.assertAlmostEqual(converted['position_xyz'][1], 22)
        self.assertEqual(converted['position_xyz'][2], 30)
        self.assertAlmostEqual(converted['rotation_basis'][1], 1)
        direct = convert_root_channels(sample, reference, reference_flags=4,
                                       translation_reference_enabled=False)
        self.assertEqual(direct['position_xyz'], [2, 0, 0])
        with self.assertRaises(ValueError):
            convert_root_channels(sample, reference, reference_flags=8,
                                  translation_reference_enabled=True)

    def test_local_matrix_channels_preserve_unwritten_components(self):
        base = rotation_matrix([0, 0, 0, 1])
        base[12:15] = [7, 8, 9]
        objects = [{'key': 'a', 'flags': '00400000', 'linked_matrix': base}]
        track = {'index': 0, 'short1': 0, 'frames': [
            {'flags': 128, 'tick_raw': 0, 'transform': {'flags': 0x10,
             'quaternion_xyzw': [0, 0, 1, 0]}}]}
        result = sample_clone_local_matrices({'tracks': [track]}, objects, 0)
        matrix = result['objects'][0]['jade_destination_matrix']
        self.assertEqual(matrix[12:15], [7, 8, 9])
        self.assertEqual(matrix[0], -1)
        self.assertEqual(base[0], 1)
        self.assertTrue(result['complete_local_snapshot'])
        track['frames'][0]['transform']['flags'] |= 0x20
        self.assertFalse(sample_clone_local_matrices({'tracks': [track]}, objects, 0)['complete_local_snapshot'])

    def test_general_rotation_no_interpolation_flag(self):
        track = {'index': 0, 'short1': 0, 'frames': [
            {'flags': 0x880, 'tick_raw': 60, 'transform': {'flags': 0x10,
             'quaternion_xyzw': [0, 0, 0, 1]}},
            {'flags': 128, 'tick_raw': 0, 'transform': {'flags': 1,
             'float3_channels': [[0, 0, 0]]}}]}
        self.assertEqual(sample_local_track(track, .5)['quaternion_xyzw'], [0, 0, 0, 1])

    def test_timed_channels_and_native_endpoint_selection(self):
        track = {'index': 4, 'short1': 2, 'frames': [
            {'flags': 128, 'tick_raw': 60, 'transform': {'flags': 0x11,
             'quaternion_xyzw': [0, 0, 0, 1], 'float3_channels': [[0, 0, 0]]}},
            {'flags': 128, 'tick_raw': 0, 'transform': {'flags': 0x11,
             'quaternion_xyzw': [0, 0, 1, 0], 'float3_channels': [[4, 0, 0]]}}]}
        middle = sample_local_track(track, .5)
        self.assertEqual(middle['position_xyz'], [2, 0, 0])
        self.assertAlmostEqual(middle['quaternion_xyzw'][2], math.sqrt(.5))
        self.assertEqual(sample_local_track(track, 1)['quaternion_xyzw'], [0, 0, 1, 0])
        self.assertEqual(sample_local_track(track, 2)['position_xyz'], [4, 0, 0])
        track['frames'][0]['transform']['flags'] |= 8
        with self.assertRaises(ValueError):
            sample_local_track(track, .5)

    def test_clone_external_parent_is_cleared(self):
        rows = [{'key': 'a', 'flags': '00400000', 'linked_gao': 'external'},
                {'key': 'b', 'flags': '00400000', 'linked_gao': 'a'},
                {'key': 'c', 'flags': '00000000'}]
        mapped = clone_parent_mapping(rows)
        self.assertIsNone(mapped[0]['clone_parent'])
        self.assertEqual(mapped[1]['clone_parent'], 'a')
        self.assertEqual(mapped[2]['destination'], 'gao_matrix')

    def test_native_rotation_shortest_arc_and_half_turn(self):
        a, b = [0, 0, 0, 1], [0, 0, 1, 0]
        result = interpolate_rotation(a, b, .5)
        self.assertAlmostEqual(result[2], math.sqrt(.5))
        self.assertAlmostEqual(result[3], math.sqrt(.5))
        self.assertEqual(interpolate_rotation(a, [0, 0, 0, -1], .75), a)
        self.assertEqual(b, [0, 0, 1, 0])
        self.assertEqual(interpolate_rotation(a, b, 0), a)
        self.assertEqual(interpolate_rotation(a, b, 1), b)

    def test_native_rotation_near_equal_hold_and_validation(self):
        a = [0, 0, 0, 1]
        b = [0, 0, math.sin(.0001), math.cos(.0001)]
        self.assertEqual(interpolate_rotation(a, b, 1), a)
        with self.assertRaises(ValueError):
            interpolate_rotation(a, a, float('nan'))
        with self.assertRaises(ValueError):
            interpolate_rotation(a, [0, 0, 0, 0], .5)

    def test_native_duration_boundaries_and_carry(self):
        track = {'frames': [{'flags': 128, 'tick_raw': 30}, {'flags': 128, 'tick_raw': 60}]}
        self.assertEqual(locate_transform_segment(track, .5)['frame_index'], 0)
        self.assertEqual(locate_transform_segment(track, .5)['fraction'], 1)
        self.assertEqual(locate_transform_segment(track, .75)['segment_seconds'], .25)
        self.assertTrue(locate_transform_segment(track, 2)['clamped_terminal'])
        self.assertAlmostEqual(locate_transform_segment(track, 3.25, loop=True)['fraction'], .5)

    def test_unsupported_timing_and_zero_length(self):
        zero = {'frames': [{'flags': 128, 'tick_raw': 0}]}
        self.assertEqual(locate_transform_segment(zero, 0)['fraction'], 0)
        with self.assertRaises(ValueError):
            locate_transform_segment(zero, 1, loop=True)
        with self.assertRaises(ValueError):
            locate_transform_segment({'frames': [{'flags': 64, 'tick_raw': 1}]}, 0)
        with self.assertRaises(ValueError):
            locate_transform_segment(zero, float('nan'))

    def test_noncommuting_parent_composition(self):
        parent = rotation_matrix([0, 0, math.sqrt(.5), math.sqrt(.5)])
        parent[12:15] = [10, 0, 0]
        local = rotation_matrix([0, 0, 0, 1])
        local[12:15] = [2, 0, 0]
        result = affine_product(local, parent)
        self.assertAlmostEqual(result[12], 10)
        self.assertAlmostEqual(result[13], 2)
        rows = [{'key': 'root', 'gao_matrix': parent},
                {'key': 'child', 'linked_gao': 'root', 'linked_matrix': local,
                 'linked_matrix_flags': 2}]
        self.assertEqual(assemble_rest_pose(rows)['child'], result)
        rows[1]['linked_matrix_flags'] = 8
        with self.assertRaises(ValueError):
            assemble_rest_pose(rows)

    def test_translation_mirror_and_interpolation(self):
        points = translation_sample({'flags': 0x20, 'transform': {'float3_channels': [[2, 3, 4]]}})
        self.assertEqual(points, [[-2, 3, 4]])
        self.assertEqual(interpolate_translation([[0, 0, 0]], [4, 2, 0], .5), [2, 1, 0])
        self.assertEqual(interpolate_translation([[0, 0, 0], [0, 4, 0]], [4, 0, 0], .5), [1, 2, 0])
        self.assertEqual(interpolate_translation([[0, 0, 0], [0, 4, 0], [4, 4, 0]], [4, 0, 0], .5), [2, 3, 0])

    def test_graph_cycle_and_external_root(self):
        rows = [{'key': 'a', 'linked_gao': 'external'}, {'key': 'b', 'linked_gao': 'a'}]
        self.assertEqual(validate_link_graph(rows), {'a': 0, 'b': 1})
        rows[0]['linked_gao'] = 'b'
        with self.assertRaises(ValueError):
            validate_link_graph(rows)

    def clip(self):
        # Shared transform header + byte durations + reused frame flags, as in Sally.
        return (struct.pack('<HHHHII', 1, 2, 0xBA00, 3, 40, 2)
                + struct.pack('<BHHH3h', 8, 0x80, 10, 0x90, 0, 0, 0)
                + struct.pack('<B3h', 0, 0, 0, 32767))

    def test_shared_headers_and_extreme_quaternion(self):
        raw = self.clip()
        parsed = decode_animation(raw)
        self.assertEqual(encode_animation(parsed), raw)
        self.assertEqual(parsed['opaque_tail_hex'], '')
        samples = [f['transform']['quaternion_xyzw'] for f in parsed['tracks'][0]['frames']]
        self.assertEqual(samples, [[0, 0, 0, 1], [0, 0, 1, 0]])

    def test_truncation_at_every_offset(self):
        raw = self.clip()
        for i in range(len(raw)):
            with self.subTest(offset=i), self.assertRaises(ValueError):
                decode_animation(raw[:i])

    def test_matrix_basis_conversion(self):
        q = [0, 0, math.sqrt(.5), math.sqrt(.5)]
        matrix = rotation_matrix(q)
        # Jade +90 around Z maps X to Y; converted Bevy +90 around Y maps X to -Z.
        self.assertAlmostEqual(matrix[0], 0)
        self.assertAlmostEqual(matrix[1], 1)
        bevy = rotation_matrix([q[0], q[2], -q[1], q[3]])
        self.assertAlmostEqual(bevy[0], 0)
        self.assertAlmostEqual(bevy[2], -1)

    def test_native_mirror_and_root_mapping(self):
        q = [0, .6, 0, .8]
        parsed = {'tracks': [{'index': 0, 'short1': 65535, 'frames': [
            {'index': 0, 'tick_raw': 30, 'flags': 0x20,
             'transform': {'quaternion_xyzw': q}}]}]}
        sample = rotation_samples(parsed, ['example'])['tracks'][0]
        self.assertTrue(sample['native_slot_is_actor_root'])
        self.assertIsNone(sample['candidate_gao'])
        self.assertEqual(sample['samples'][0]['jade_quaternion_xyzw'], [0, -.6, 0, .8])
        self.assertEqual(sample['samples'][0]['native_duration_divided_by_60'], .5)


if __name__ == '__main__':
    unittest.main()
