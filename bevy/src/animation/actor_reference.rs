//! No-scale actor-relative root translation (140b49fb0).
//! Reference selection and callback input timing remain caller responsibilities.
use super::hierarchy::{affine_product, IDENTITY};

pub fn inverse_no_scale(matrix: [f32; 16], flags: u32) -> Result<([f32; 16], u32), &'static str> {
    if flags & 8 != 0 {
        return Err("Scaled actor/root inverse unsupported");
    }
    if matrix.iter().any(|v| !v.is_finite()) {
        return Err("Nonfinite actor matrix");
    }
    let mut result = IDENTITY;
    for column in 0..3 {
        for row in 0..3 {
            result[column * 4 + row] = matrix[row * 4 + column];
        }
    }
    let negative = [-matrix[12], -matrix[13], -matrix[14]];
    for row in 0..3 {
        result[12 + row] = (result[row] * negative[0] + result[4 + row] * negative[1])
            + result[8 + row] * negative[2];
    }
    Ok((result, flags))
}

pub fn actor_reference_position(
    position: [f32; 3],
    reference: [f32; 16],
    reference_flags: u32,
    actor: [f32; 16],
    actor_flags: u32,
    height: f32,
    add_height: bool,
) -> Result<[f32; 3], &'static str> {
    if position.iter().any(|v| !v.is_finite()) || !height.is_finite() {
        return Err("Nonfinite position or height");
    }
    let (inverse, flags) = inverse_no_scale(actor, actor_flags)?;
    let (relative, _) = affine_product(&reference, &inverse, reference_flags, flags)?;
    let mut output = [0.; 3];
    for row in 0..3 {
        let [a, b, c] = if row == 0 { [0, 1, 2] } else { [1, 0, 2] };
        output[row] = ((position[a] * relative[a * 4 + row] + position[b] * relative[b * 4 + row])
            + position[c] * relative[c * 4 + row])
            + relative[12 + row];
    }
    if add_height {
        output[2] += height;
    }
    Ok(output)
}

pub fn refresh_reference(
    root: [f32; 16],
    root_flags: u32,
    saved_actor: [f32; 16],
    saved_flags: u32,
) -> Result<([f32; 16], u32), &'static str> {
    let (inverse, flags) = inverse_no_scale(root, root_flags)?;
    affine_product(&inverse, &saved_actor, flags, saved_flags)
}

///140ae9870 basis-only reference*local, with its flag-selected identity paths.
/// Scale/alternate basis flags are outside the reconstructed branch.
pub fn compose_reference_basis(
    mut destination: [f32; 16],
    destination_flags: u32,
    local: [f32; 16],
    local_flags: u32,
    reference: [f32; 16],
    reference_flags: u32,
) -> Result<([f32; 16], u32), &'static str> {
    if (local_flags | reference_flags) & 0x38 != 0 {
        return Err("Scaled or alternate reference basis unsupported");
    }
    if destination
        .iter()
        .chain(local.iter())
        .chain(reference.iter())
        .any(|v| !v.is_finite())
    {
        return Err("Nonfinite reference basis");
    }
    let indices = [0, 1, 2, 4, 5, 6, 8, 9, 10];
    let written_flags;
    if local_flags & 0x3c == 0 {
        for i in indices {
            destination[i] = reference[i];
        }
        written_flags = reference_flags;
    } else if reference_flags & 0x3c == 0 {
        for i in indices {
            destination[i] = local[i];
        }
        written_flags = local_flags;
    } else {
        let l = local;
        let r = reference;
        destination[0] = (l[0] * r[0] + l[1] * r[4]) + r[8] * l[2];
        destination[1] = (l[1] * r[5] + r[1] * l[0]) + l[2] * r[9];
        destination[2] = (l[0] * r[2] + l[1] * r[6]) + r[10] * l[2];
        destination[4] = (l[5] * r[4] + r[0] * l[4]) + r[8] * l[6];
        destination[5] = (r[1] * l[4] + l[5] * r[5]) + l[6] * r[9];
        destination[6] = (l[5] * r[6] + r[2] * l[4]) + r[10] * l[6];
        destination[8] = (l[8] * r[0] + l[9] * r[4]) + r[8] * l[10];
        destination[9] = (l[8] * r[1] + l[9] * r[5]) + r[9] * l[10];
        destination[10] = (l[9] * r[6] + l[8] * r[2]) + r[10] * l[10];
        written_flags = local_flags | reference_flags;
    }
    Ok((destination, destination_flags | (written_flags & 4)))
}

pub fn actor_relative_reference(
    reference: [f32; 16],
    reference_flags: u32,
    actor: [f32; 16],
    actor_flags: u32,
) -> Result<([f32; 16], u32), &'static str> {
    let (inverse, flags) = inverse_no_scale(actor, actor_flags)?;
    affine_product(&reference, &inverse, reference_flags, flags)
}

#[cfg(test)]
#[path = "../../tests/unit/animation/actor_reference.rs"]
mod tests;
