//! Native no-scale local pose blend (140aed7b0/140aed150/140aecd40).
//! Matrices retain Jade column-major axes. Host trig is numerical, not bit-exact
//! native math-library parity. Root reference and tracking are separate stages.
use super::transition::blend_saved_primary_position;

pub(super) fn normalize_quaternion(q: [f32; 4]) -> Result<[f32; 4], &'static str> {
    let [x, y, z, w] = q;
    let squared = ((y * y + x * x) + z * z) + w * w;
    if !squared.is_finite() || squared <= 0.0 {
        return Err("Invalid quaternion norm");
    }
    let inverse = 1.0 / squared.sqrt();
    Ok(q.map(|v| v * inverse))
}

pub fn matrix_quaternion(m: [f32; 16]) -> Result<[f32; 4], &'static str> {
    if m.iter().any(|v| !v.is_finite()) {
        return Err("Finite matrix required");
    }
    let (x, y, z) = (m[0], m[5], m[10]);
    let trace = (x + y) + z;
    let (branch, radicand) = if trace > 0.0 {
        (3, trace + 1.0)
    } else if x < y {
        if y < z {
            (2, ((1.0 - x) - y) + z)
        } else {
            (1, ((1.0 - x) + y) - z)
        }
    } else if z <= x {
        (0, ((x + 1.0) - y) - z)
    } else {
        (2, ((1.0 - x) - y) + z)
    };
    if !radicand.is_finite() || radicand <= 0.0 {
        return Err("Invalid matrix quaternion branch");
    }
    let root = radicand.sqrt();
    let factor = 0.5 / root;
    let q = match branch {
        3 => [
            (m[6] - m[9]) * factor,
            (m[8] - m[2]) * factor,
            (m[1] - m[4]) * factor,
            root * 0.5,
        ],
        0 => [
            root * 0.5,
            (m[4] + m[1]) * factor,
            (m[8] + m[2]) * factor,
            (m[6] - m[9]) * factor,
        ],
        1 => [
            (m[4] + m[1]) * factor,
            root * 0.5,
            (m[9] + m[6]) * factor,
            (m[8] - m[2]) * factor,
        ],
        _ => [
            (m[8] + m[2]) * factor,
            (m[9] + m[6]) * factor,
            root * 0.5,
            (m[1] - m[4]) * factor,
        ],
    };
    normalize_quaternion(q)
}

pub fn quaternion_matrix(q: [f32; 4]) -> [f32; 16] {
    let [x, y, z, w] = q;
    let (xx, yy, zz) = (x + x, y + y, z + z);
    let (a, b, c) = (0.5 - xx * x, 0.5 - yy * y, 0.5 - zz * z);
    let zw = zz * w;
    [
        c + b,
        zw + xx * y,
        xx * z - yy * w,
        0.0,
        xx * y - zw,
        c + a,
        yy * z + xx * w,
        0.0,
        yy * w + xx * z,
        yy * z - xx * w,
        b + a,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
    ]
}

pub fn blend_rotation(a: [f32; 4], mut b: [f32; 4], weight: f32) -> Result<[f32; 4], &'static str> {
    if a.iter().chain(&b).any(|v| !v.is_finite()) || !weight.is_finite() {
        return Err("Finite quaternion blend required");
    }
    let mut dot = ((a[0] * b[0] + a[1] * b[1]) + a[2] * b[2]) + a[3] * b[3];
    if dot < 0.0 {
        dot = -dot;
        b = b.map(|v| -v);
    }
    if dot.abs() >= f32::from_bits(0x3f7ffffe) {
        return Ok(a);
    }
    let angle = (f64::from(dot).acos()) as f32;
    let reciprocal = 1.0 / (1.0 - dot * dot).sqrt();
    // Rotation weight is intentionally not clamped by this native consumer.
    let left = f64::from((1.0 - weight) * angle).sin() as f32 * reciprocal;
    let right = f64::from(weight * angle).sin() as f32 * reciprocal;
    normalize_quaternion(std::array::from_fn(|i| a[i] * left + b[i] * right))
}

pub fn blend_local_no_scale(
    incoming: [f32; 16],
    incoming_flags: u32,
    saved_primary: [f32; 16],
    primary_flags: u32,
    weight: f32,
) -> Result<[f32; 16], &'static str> {
    if (incoming_flags | primary_flags) & 8 != 0 {
        return Err("Scaled local blend not reconstructed");
    }
    let q = blend_rotation(
        matrix_quaternion(incoming)?,
        matrix_quaternion(saved_primary)?,
        weight,
    )?;
    let mut result = quaternion_matrix(q);
    let position = blend_saved_primary_position(
        [saved_primary[12], saved_primary[13], saved_primary[14]],
        [incoming[12], incoming[13], incoming[14]],
        weight,
    )?;
    result[12..15].copy_from_slice(&position);
    Ok(result)
}

#[cfg(test)]
#[path = "../../tests/unit/animation/pose_blend.rs"]
mod tests;
