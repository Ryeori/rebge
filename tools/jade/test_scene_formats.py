from project_paths import PROJECT_ROOT, report_path
import struct,unittest
from jade_mesh import parse_mesh,Cursor
from jade_texture import parse_texture,color_image
def mesh_bytes(indices=(0,1,2)):
    return (struct.pack('<9I',1,0,3,0,3,1,0,0,0)+struct.pack('<9f',0,0,0,1,0,0,0,1,0)+bytes(36)
        +struct.pack('<6f',0,0,1,0,0,1)+struct.pack('<4I',1,0,0,0)+bytes(24)
        +struct.pack('<6H2I',*indices,0,1,2,0,0)+struct.pack('<I',0))
def texture_bytes():
    footer=struct.pack('<IHBBHH5I',0xffffffff,4,13,16,4,4,0,0,0xcad01234,0xff00ff,0xc0dec0de)
    return struct.pack('<H5IBI',14,1,1,2,16,8,0,1)+struct.pack('<HHI',0xf800,0,0)+bytes(4)+footer
class Formats(unittest.TestCase):
    def test_mesh_triangle(self):
        mesh=parse_mesh(mesh_bytes());self.assertEqual(mesh['positions'][1],(1.,0.,0.));self.assertEqual(mesh['submeshes'][0]['triangles'][0][:3],(0,1,2))
    def test_mesh_invalid_index(self):
        with self.assertRaisesRegex(ValueError,'index'):parse_mesh(mesh_bytes((0,1,3)))
    def test_mesh_truncated(self):
        with self.assertRaises(ValueError):parse_mesh(mesh_bytes()[:-8])
    def test_texture_bc1_red(self):
        info,image=color_image(texture_bytes());self.assertEqual(image.size,(4,4));self.assertEqual(image.getpixel((1,1)),(255,0,0,255));self.assertEqual(info['count'],1)
    def test_texture_invalid_stream(self):
        data=bytearray(texture_bytes());struct.pack_into('<I',data,18,10000)
        with self.assertRaises(ValueError):parse_texture(bytes(data))
    def test_cursor_roundtrip_unknown_gap(self):
        c=Cursor(b'\x01\x00\x00\x00\xaa\xbb\xcc\xdd');self.assertEqual(c.read('I'),1);c.skip(4);self.assertEqual(c.rebuild(),c.data)
if __name__=='__main__':unittest.main()
