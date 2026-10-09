from project_paths import PROJECT_ROOT, report_path
import pathlib,struct,tempfile,unittest
from jade_localization import parse_pair,encode_txi,display_text
from bpak_reader import entries
class FormatTests(unittest.TestCase):
 def test_offsets_padding_and_roundtrip(self):
  field=b'line\0'+bytes([0xcc])*59;txi=struct.pack('<I',2)+field;txs=b'xxhello\0unused\0'
  records=parse_pair(txi,txs)
  self.assertEqual(records[0]['text_source'],'hello');self.assertEqual(encode_txi(records),txi)
 def test_bad_stride_offset_and_termination(self):
  for txi,txs in [(b'x',b''),(struct.pack('<I',9)+bytes(64),b'a\0'),(bytes(68),b'abc')]:
   with self.assertRaises(ValueError):parse_pair(txi,txs)
 def test_unicode_and_control_preservation(self):
  self.assertEqual(display_text(b'\\P26\\\\U+1064\\'),'\\P26\\'+chr(1064))
  self.assertEqual(display_text(b'\\U+1114112\\'),'\\U+1114112\\')
 def test_malformed_pak(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp)/'bad.pak'
   for data in [b'BPAK',struct.pack('<4s5I',b'BPAK',1,1,0,100,0),struct.pack('<4s5I',b'BPAK',1,1,0,1,29)+b'\0'+struct.pack('<I',100)+bytes(24)]:
    p.write_bytes(data)
    with self.assertRaises(ValueError):list(entries(p))
if __name__=='__main__':unittest.main()
