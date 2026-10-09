import unittest
from jade_matrix_quaternion import matrix_quaternion,normalize_quaternion
from jade_pose import rotation_matrix


class MatrixQuaternionTests(unittest.TestCase):
    def test_trace_and_three_dominant_axis_branches(self):
        for q in ([0,0,0,1],[1,0,0,0],[0,1,0,0],[0,0,1,0],
                  [0.5,0.5,0.5,0.5],[-0.8,0.4,0.2,0.4]):
            q=normalize_quaternion(q)
            actual=matrix_quaternion(rotation_matrix(q))
            error=min(max(abs(a-b) for a,b in zip(q,actual)),
                      max(abs(a+b) for a,b in zip(q,actual)))
            self.assertLess(error,2e-7)

    def test_translation_does_not_change_rotation(self):
        m=rotation_matrix([0,0,0,1]);m[12:15]=[10,20,30]
        self.assertEqual(matrix_quaternion(m),[0,0,0,1])

    def test_zero_quaternion_rejected(self):
        with self.assertRaises(ValueError):normalize_quaternion([0,0,0,0])


if __name__=='__main__':unittest.main()
