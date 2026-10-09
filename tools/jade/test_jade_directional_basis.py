import unittest

from jade_directional_basis import directional_basis


class DirectionTests(unittest.TestCase):
    matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 7, 8, 9, 1]

    def test_forward_is_negative_y(self):
        result, flags = directional_basis(self.matrix, 8, [0, -2, 0], [0, 0, 3])
        self.assertEqual(result, self.matrix)
        self.assertEqual(flags, 12)

    def test_direction_changes_basis_preserves_translation(self):
        result, _ = directional_basis(self.matrix, 0, [1, 0, 0], [0, 0, 1])
        self.assertEqual(result[:3], [0, 1, 0])
        self.assertEqual(result[4:7], [-1, 0, 0])
        self.assertEqual(result[8:11], [0, 0, 1])
        self.assertEqual(result[12:], self.matrix[12:])

    def test_existing_z_branch(self):
        result, _ = directional_basis(self.matrix, 0, [0, -1, 0])
        # Null-up path uses Z cross Y without supplied-up branch sign flip.
        self.assertEqual(result[:3], [-1, 0, 0])
        self.assertEqual(result[4:7], [0, 1, 0])
        self.assertEqual(result[8:11], [0, 0, -1])

    def test_parallel_fallback_explicit(self):
        with self.assertRaises(NotImplementedError):
            directional_basis(self.matrix, 0, [0, 0, 1], [0, 0, 1])
        with self.assertRaises(ValueError):
            directional_basis(self.matrix, 0, [0, 0, 0])


if __name__ == '__main__':
    unittest.main()
