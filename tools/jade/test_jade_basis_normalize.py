import unittest

from jade_basis_normalize import normalize_basis, normalize_vector


class BasisTests(unittest.TestCase):
    def test_original_y_is_reconstructed_from_z_cross_x(self):
        matrix = [2, 0, 0, 4, 99, 99, 99, 5, 1, 0, 3, 6, 7, 8, 9, 1]
        result = normalize_basis(matrix)
        self.assertEqual(result[:3], [1, 0, 0])
        self.assertEqual(result[4:7], [0, 1, 0])
        self.assertEqual(result[8:11], [0, 0, 1])
        self.assertEqual([result[i] for i in (3, 7, 11, 12, 13, 14, 15)],
                         [matrix[i] for i in (3, 7, 11, 12, 13, 14, 15)])

    def test_handedness_follows_z(self):
        matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, -2, 0, 0, 0, 0, 1]
        result = normalize_basis(matrix)
        self.assertEqual(result[4:7], [0, -1, 0])
        self.assertEqual(result[8:11], [0, 0, -1])

    def test_zero_and_parallel_are_not_replaced_by_identity(self):
        self.assertEqual(normalize_vector([0, 0, 0]), [0, 0, 0])
        matrix = [1, 0, 0, 0, 0, 1, 0, 0, 2, 0, 0, 0, 0, 0, 0, 1]
        result = normalize_basis(matrix)
        self.assertEqual(result[4:7], [0, 0, 0])
        self.assertEqual(result[8:11], [0, 0, 0])


if __name__ == '__main__':
    unittest.main()
