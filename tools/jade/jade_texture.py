"""Jade Anniversary texture container and first color stream to standard DDS."""
from project_paths import PROJECT_ROOT, report_path
import struct,io,hashlib
from PIL import Image
def parse_texture(data):
    if len(data)<59:raise ValueError('Texture too short')
    magic,kind,count,unknown,primary,secondary,alpha,levels=struct.unpack_from('<H5IBI',data)
    if magic!=14 or not 1<=count<=4:raise ValueError('Unsupported texture container')
    footer=data[-32:];width,height=struct.unpack_from('<2H',footer,8)
    if footer[-12:]!=bytes.fromhex('3412d0caff00ff00dec0dec0'):raise ValueError('Invalid texture footer')
    first=primary if alpha else secondary
    if kind==5:secondary=first
    sizes=[first]+[secondary]*(count-1);offset=27;streams=[]
    for size in sizes:
        if size>len(data)-32-offset:raise ValueError('Texture stream out of bounds')
        streams.append(data[offset:offset+size]);offset+=size
    extension=data[offset:-32]
    rebuilt=struct.pack('<H5IBI',magic,kind,count,unknown,primary,struct.unpack_from('<I',data,18)[0],alpha,levels)+b''.join(streams)+extension+footer
    if rebuilt!=data:raise ValueError('Texture round trip failed')
    if not 0<width<=16384 or not 0<height<=16384:raise ValueError('Invalid texture dimensions')
    block=16 if alpha else 8
    top=max(1,(width+3)//4)*max(1,(height+3)//4)*block
    if first<top:raise ValueError('Color stream too short for dimensions')
    # BC1/BC3 interpretation also checked against encoded length and visual inspection.
    return {'kind':kind,'count':count,'width':width,'height':height,'levels':levels,'alpha':bool(alpha),
            'streams':streams,'extension':extension,'sha256':hashlib.sha256(data).hexdigest()}
def first_dds(texture):
    w,h=texture['width'],texture['height'];fourcc=b'DXT5' if texture['alpha'] else b'DXT1'
    block=16 if texture['alpha'] else 8;size=max(1,(w+3)//4)*max(1,(h+3)//4)*block
    header=struct.pack('<7I',124,0x81007,h,w,size,0,1)+bytes(44)
    header+=struct.pack('<2I4s5I',32,4,fourcc,0,0,0,0,0)+struct.pack('<5I',0x1000,0,0,0,0)
    return b'DDS '+header+texture['streams'][0][:size]
def color_image(data):
    texture=parse_texture(data)
    im=Image.open(io.BytesIO(first_dds(texture)));im.load()
    return texture,im.convert('RGBA')
