import unittest

from jade_tracking_rotation import rotate_yz_basis, rotate_world_xy


class RotationTests(unittest.TestCase):
    def setUp(self):
        self.matrix = [1, 0, 0, 0, 0, 1, 0, 0,
                       0, 0, 1, 0, 7, 8, 9, 1]

    def test_quarter_turn_sign_and_translation(self):
        result, flags = rotate_yz_basis(self.matrix, 8, 0, 1)
        self.assertEqual(result[4:7], [0, 0, 1])
        self.assertEqual(result[8:11], [0, -1, 0])
        self.assertEqual(result[:4], self.matrix[:4])
        self.assertEqual(result[12:], self.matrix[12:])
        self.assertEqual(flags, 12)

    def test_inverse_preserves_scaled_basis(self):
        self.matrix[5], self.matrix[10] = 2, 3
        rotated, flags = rotate_yz_basis(self.matrix, 0, 0, 1)
        recovered, _ = rotate_yz_basis(rotated, flags, 0, -1)
        self.assertEqual(recovered, self.matrix)

    def test_identity_marks_rotation(self):
        result, flags = rotate_yz_basis(self.matrix, 0, 1, 0)
        self.assertEqual(result, self.matrix)
        self.assertEqual(flags, 4)

    def test_world_yaw_rotates_all_basis_columns_not_translation(self):
        result, flags = rotate_world_xy(self.matrix, 8, 0, 1)
        self.assertEqual(result[:3], [0, 1, 0])
        self.assertEqual(result[4:7], [-1, 0, 0])
        self.assertEqual(result[8:11], [0, 0, 1])
        self.assertEqual(result[12:], self.matrix[12:])
        self.assertEqual(flags, 12)
        restored, _ = rotate_world_xy(result, flags, 0, -1)
        self.assertEqual(restored, self.matrix)


if __name__ == '__main__':
    unittest.main()
