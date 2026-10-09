import sys,struct,unittest
sys.path.insert(0,'tools/jade')
from jade_skin import decode_skin_word,deform_vertices
class SkinTests(unittest.TestCase):
 def test_shared_word_bits(self):
  r=decode_skin_word(0x3f800001);self.assertEqual(r['vertex'],1);self.assertGreater(r['weight'],1)
 def test_accumulation_no_normalization(self):
  m=[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,3.,0.,0.,1.]
  records=[{'index_u16':0,'words_u32':[0x3f000000]},{'index_u16':1,'words_u32':[0x3f000000]}]
  out=deform_vertices([[2.,0.,0.]],records,{0:{'matrix':m,'flags':2},1:{'matrix':m,'flags':0}});self.assertEqual(out,[[3.5,0.,0.]])
 def test_bounds(self):
  with self.assertRaises(ValueError):deform_vertices([[0.,0.,0.]],[{'index_u16':0,'words_u32':[0x3f800001]}],{0:{'matrix':[0.]*16,'flags':0}})
 def test_all_modes(self):
  m=[0.,1.,0.,2.,-1.,0.,0.,3.,0.,0.,1.,4.,10.,20.,30.,1.]
  expected={0:[1,2,3],2:[11,22,33],4:[-2,1,3],6:[8,21,33],8:[2,6,12],10:[12,26,42],12:[-6,2,12],14:[4,22,42]}
  for mode,value in expected.items():self.assertEqual(deform_vertices([[1.,2.,3.]],[{'index_u16':0,'words_u32':[0x3f800000]}],{0:{'matrix':m,'flags':mode}}),[value])
if __name__=='__main__':unittest.main()
