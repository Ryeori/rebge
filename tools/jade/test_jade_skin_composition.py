import unittest
from jade_skin import compose_skin_matrix,deform_vertices

class CompositionTests(unittest.TestCase):
 def test_native_order_noncommuting(self):
  bind=[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,2.,0.,0.,1.]
  bone=[0.,1.,0.,0.,-1.,0.,0.,0.,0.,0.,1.,0.,10.,20.,30.,1.]
  result=compose_skin_matrix(bind,2,bone,6)
  self.assertEqual(result['matrix'][12:15],[10.,22.,30.])
  self.assertEqual(deform_vertices([[0.,0.,0.]],[{'index_u16':0,'words_u32':[0x3f800000]}],{0:result}),[[10.,22.,30.]])
 def test_flags_override_zero_storage(self):
  result=compose_skin_matrix([0.]*16,0,[0.]*16,0)
  self.assertEqual(result['flags'],0)
  self.assertEqual(deform_vertices([[1.,2.,3.]],[{'index_u16':0,'words_u32':[0x3f800000]}],{0:result}),[[1.,2.,3.]])
 def test_scale_rejected(self):
  with self.assertRaises(NotImplementedError):compose_skin_matrix([0.]*16,8,[0.]*16,0)

if __name__=='__main__':unittest.main()
