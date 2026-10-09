//! Bounded eye-material path: 140a3c700 mode6 + 140a3f750 packed transform.
//! Only indexed no-scale bone projection onto X/Z, without animated offsets/rotation.
use super::actor_reference::inverse_no_scale;
use serde::Deserialize;

#[derive(Deserialize)]
pub struct BoneProjection {
    pub descriptor: u16,
    pub flags: u32,
    pub packed_u: u32,
    pub packed_v: u32,
}
pub fn project(
    input: &BoneProjection,
    positions: &[[f32; 3]],
    palette: &[([f32; 16], u32)],
) -> Result<Vec<[f32; 2]>, &'static str> {
    if input.flags >> 20 & 15 != 6
        || input.flags & 0xc0000000 != 0
        || input.descriptor & 0xc0 != 0xc0
        || input.descriptor >> 4 & 3 != 1
    {
        return Err("Unsupported material projection mode");
    }
    let rotation = ((input.packed_v >> 2 & 0x4000 | input.packed_u & 0x10000) >> 13)
        | ((input.packed_u & 1) << 2)
        | (input.packed_v & 1);
    if rotation != 0 {
        return Err("Rotated material UV unsupported");
    }
    let slot = (input.descriptor >> 8 & 7) as usize;
    let (matrix, flags) = *palette
        .get(slot)
        .ok_or("Missing material projection bone")?;
    let (inverse, _) = inverse_no_scale(matrix, flags)?;
    let scale_u = f32::from_bits(input.packed_u & 0xfffe0000);
    let scale_v = f32::from_bits(input.packed_v & 0xfffe0000);
    // Assembly stores shifted/masked bits directly; these are not integer-to-float casts.
    let offset = |word: u32| {
        if word == 0 || word == 0x08001000 {
            0.
        } else {
            f32::from_bits(word << 16)
        }
    };
    let offset_u = offset(input.packed_u) * scale_u;
    let offset_v = offset(input.packed_v) * scale_v;
    positions
        .iter()
        .map(|p| {
            let x = ((inverse[4] * p[1] + inverse[0] * p[0]) + inverse[8] * p[2]) + inverse[12];
            let z = ((inverse[6] * p[1] + inverse[2] * p[0]) + inverse[10] * p[2]) + inverse[14];
            let uv = [
                (scale_u * x + 0. * z) + offset_u,
                (0. * x + scale_v * z) + offset_v,
            ];
            if uv.iter().any(|v| !v.is_finite()) {
                Err("Nonfinite projected UV")
            } else {
                Ok(uv)
            }
        })
        .collect()
}
