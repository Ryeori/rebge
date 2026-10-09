//! Byte-preserving modifier24 prepare/finalize lifecycle.
//! Dynamic world writer and global processed-list discovery are separate.
use super::reference_entry::MatrixStorage;

pub type State = [u8; 256];

pub struct Finalized {
    pub state: State,
    pub restored_local: MatrixStorage,
}

/// Backup-only part of1409ddef0. Parent recursion, parameter inheritance,
/// world evaluation, processed marker and list insertion remain caller stages.
/// Local must be supplied at the native save point after parent preparation.
pub fn save_prepare_inputs(state: &State, local: MatrixStorage) -> State {
    let mut prepared = *state;
    for (source, destination, size) in [
        (4, 0x50, 4),
        (8, 0x54, 4),
        (0xd8, 0xdc, 4),
        (0xec, 0xf0, 4),
        (0xa8, 0xc0, 12),
        (0xb4, 0xcc, 12),
    ] {
        prepared[destination..destination + size].copy_from_slice(&state[source..source + size]);
    }
    if u32::from_le_bytes(state[4..8].try_into().unwrap()) & 0x10000000 == 0 {
        for (index, value) in local.values.iter().enumerate() {
            prepared[0xc + index * 4..0x10 + index * 4].copy_from_slice(&value.to_le_bytes());
        }
        prepared[0x4c..0x50].copy_from_slice(&local.flags.to_le_bytes());
    }
    prepared
}

/// One explicitly supplied processed node from1409ddda0. The caller owns list
/// membership and node order; mode bit28 alone does not establish membership.
pub fn finalize(state: &State, processed_list_member: bool) -> Option<Finalized> {
    if !processed_list_member {
        return None;
    }
    let mut finalized = *state;
    for (source, destination, size) in [
        (0x54, 8, 4),
        (0xdc, 0xd8, 4),
        (0xf0, 0xec, 4),
        (0xc0, 0xa8, 12),
        (0xcc, 0xb4, 12),
    ] {
        finalized[destination..destination + size].copy_from_slice(&state[source..source + size]);
    }
    let mode = u32::from_le_bytes(state[0x50..0x54].try_into().unwrap()) & !0x10000000;
    finalized[4..8].copy_from_slice(&mode.to_le_bytes());
    let values = std::array::from_fn(|i| {
        f32::from_le_bytes(state[0xc + i * 4..0x10 + i * 4].try_into().unwrap())
    });
    let flags = u32::from_le_bytes(state[0x4c..0x50].try_into().unwrap());
    Some(Finalized {
        state: finalized,
        restored_local: MatrixStorage { values, flags },
    })
}

pub struct LinkedPublication {
    pub state: State,
    pub processed_list_member: bool,
    /// Explicit world already produced by modifier/world/palette stages.
    pub published_world: MatrixStorage,
}

fn read_float(state: &State, offset: usize) -> f32 {
    f32::from_le_bytes(state[offset..offset + 4].try_into().unwrap())
}
fn write_float(state: &mut State, offset: usize, value: f32) {
    state[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
}

pub fn damping_weight(damping: f32, delta: f32) -> Result<f32, &'static str> {
    if !damping.is_finite() || !delta.is_finite() {
        return Err("Nonfinite modifier damping/delta");
    }
    let loss = (1. - damping).max(0.);
    let factor = 1. - loss * loss;
    let mut elapsed = 0.;
    let mut retained = 1.;
    let quantum = f32::from_bits(0x3b5a740e);
    for _ in 0..4096 {
        if elapsed >= delta {
            let weight = 1. - retained;
            return if f32::is_finite(weight) {
                Ok(weight)
            } else {
                Err("Modifier damping overflow")
            };
        }
        elapsed += quantum;
        retained *= factor;
    }
    Err("Modifier delta exceeds iteration bound")
}

fn length(vector: [f32; 3], xy_first: bool) -> Result<f32, &'static str> {
    let [x, y, z] = vector;
    let squared = if xy_first {
        (x * x + y * y) + z * z
    } else {
        (y * y + x * x) + z * z
    };
    if !squared.is_finite() || squared < 0. {
        return Err("Modifier direction length overflow");
    }
    Ok((f64::from(squared).sqrt()) as f32)
}
fn unit(vector: [f32; 3], xy_first: bool, allow_zero: bool) -> Result<[f32; 3], &'static str> {
    let size = length(vector, xy_first)?;
    if size == 0. {
        return if allow_zero {
            Ok(vector)
        } else {
            Err("Degenerate modifier direction")
        };
    }
    let inverse = 1. / size;
    Ok(vector.map(|v| v * inverse))
}
fn cross(a: [f32; 3], b: [f32; 3]) -> [f32; 3] {
    [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]
}

/// Finite 140aed9a0 ordinary basis normalization. Preserve other matrix bytes.
pub fn normalize_basis(mut matrix: MatrixStorage) -> Result<MatrixStorage, &'static str> {
    if matrix.values.iter().any(|v| !v.is_finite()) || matrix.flags & 8 != 0 {
        return Err("Nonfinite or scaled modifier basis normalization");
    }
    let x = unit(matrix.values[..3].try_into().unwrap(), true, true)?;
    let y = unit(
        cross(matrix.values[8..11].try_into().unwrap(), x),
        true,
        true,
    )?;
    let z = unit(cross(x, y), true, true)?;
    matrix.values[..3].copy_from_slice(&x);
    matrix.values[4..7].copy_from_slice(&y);
    matrix.values[8..11].copy_from_slice(&z);
    Ok(matrix)
}

pub struct Step {
    pub state: State,
    pub world: MatrixStorage,
    pub effective_mode: u32,
    pub weight: f32,
}

pub struct LinkedEvaluation {
    pub step: Step,
    pub corrected_local: MatrixStorage,
}

/// Numerical end of1409ddef0: writer output -> linked local using inverse parent.
/// State must already contain saved pre-correction local and effective inherited
/// parameters. This does not run parent recursion or insert native list pointers.
pub fn evaluate_prepared_linked(
    prepared: &State,
    nominal: MatrixStorage,
    parent: MatrixStorage,
    delta: f32,
) -> Result<LinkedEvaluation, &'static str> {
    let result = step(prepared, nominal, Some(parent), delta)?;
    let (inverse, inverse_flags) =
        super::actor_reference::inverse_no_scale(parent.values, parent.flags)?;
    let (values, flags) = super::hierarchy::affine_product(
        &result.world.values,
        &inverse,
        result.world.flags,
        inverse_flags,
    )?;
    Ok(LinkedEvaluation {
        step: result,
        corrected_local: MatrixStorage { values, flags },
    })
}

impl LinkedEvaluation {
    /// Preserve writer-time output for finalization. Membership is explicit;
    /// downstream world/basis normalization may supply a different publication.
    pub fn publication(
        &self,
        processed_list_member: bool,
        published_world: MatrixStorage,
    ) -> LinkedPublication {
        LinkedPublication {
            state: self.step.state,
            processed_list_member,
            published_world,
        }
    }
}

/// Restricted finite no-scale1409dcba0 writer. Parent/global inheritance,
/// processed-list insertion, linked local correction and palette publication
/// are separate. Antiparallel directions and alternate evaluator1000 fail.
pub fn step(
    state: &State,
    nominal: MatrixStorage,
    parent: Option<MatrixStorage>,
    delta: f32,
) -> Result<Step, &'static str> {
    use super::{
        actor_reference::compose_reference_basis, hierarchy::affine_product,
        pose_blend::quaternion_matrix,
    };
    if nominal.flags & 8 != 0
        || nominal.values.iter().any(|v| !v.is_finite())
        || parent
            .as_ref()
            .is_some_and(|p| p.flags & 8 != 0 || p.values.iter().any(|v| !v.is_finite()))
    {
        return Err("Nonfinite or scaled modifier writer input");
    }
    let mut mode = u32::from_le_bytes(state[4..8].try_into().unwrap());
    if mode & 0x1000 != 0 {
        return Err("Alternate modifier evaluator unsupported");
    }
    if parent.is_none() {
        mode &= !8;
    }
    if mode & 8 != 0 {
        mode &= !2;
    }
    let weight = damping_weight(read_float(state, 8), delta)?;
    let mut output = *state;
    let mut world = nominal;
    if mode & 9 != 0 {
        let mut prior = std::array::from_fn::<_, 3, _>(|i| read_float(state, 0x88 + i * 4));
        if prior.iter().any(|v| v.is_nan()) {
            prior = [0.; 3];
        }
        if prior.iter().any(|v| !v.is_finite()) {
            return Err("Infinite modifier history unsupported");
        }
        let mut position: [f32; 3] =
            std::array::from_fn(|i| (nominal.values[12 + i] - prior[i]) * weight + prior[i]);
        if mode & 8 != 0 {
            let parent = parent.unwrap();
            let height = read_float(state, 0xd8);
            if !height.is_finite() {
                return Err("Nonfinite modifier height");
            }
            position[2] = weight * height + position[2];
            if mode & 0x400 != 0 {
                let saved = std::array::from_fn(|i| read_float(state, 0xc + i * 4));
                let saved_flags = u32::from_le_bytes(state[0x4c..0x50].try_into().unwrap());
                let (base, _) = affine_product(&saved, &parent.values, saved_flags, parent.flags)?;
                let offset: [f32; 3] = std::array::from_fn(|i| position[i] - base[12 + i]);
                let mut coordinates = [0.; 3];
                for i in 0..3 {
                    let low = read_float(state, 0xa8 + i * 4);
                    let high = read_float(state, 0xb4 + i * 4);
                    if !low.is_finite() || !high.is_finite() {
                        return Err("Nonfinite modifier bounds");
                    }
                    let value = (offset[1] * base[i * 4 + 1] + offset[0] * base[i * 4])
                        + offset[2] * base[i * 4 + 2];
                    coordinates[i] = value.max(low).min(high);
                }
                position = std::array::from_fn(|row| {
                    ((base[4 + row] * coordinates[1] + base[row] * coordinates[0])
                        + base[8 + row] * coordinates[2])
                        + base[12 + row]
                });
            }
            let original: [f32; 3] =
                std::array::from_fn(|i| nominal.values[12 + i] - parent.values[12 + i]);
            let lagged: [f32; 3] = std::array::from_fn(|i| position[i] - parent.values[12 + i]);
            let original_length = length(original, false)?;
            let lagged_length = length(lagged, false)?;
            if lagged_length != 0. {
                let ratio = original_length / lagged_length;
                position = std::array::from_fn(|i| ratio * lagged[i] + parent.values[12 + i]);
                if original_length != 0. {
                    let a = original.map(|v| (1. / original_length) * v);
                    let b = lagged.map(|v| (1. / lagged_length) * v);
                    let half = unit(std::array::from_fn(|i| b[i] + a[i]), false, false)?;
                    let xyz = cross(a, half);
                    let quaternion = [
                        xyz[0],
                        xyz[1],
                        xyz[2],
                        (half[1] * a[1] + half[0] * a[0]) + half[2] * a[2],
                    ];
                    (world.values, world.flags) = compose_reference_basis(
                        world.values,
                        world.flags,
                        nominal.values,
                        nominal.flags,
                        quaternion_matrix(quaternion),
                        4,
                    )?;
                }
            }
        }
        for i in 0..3 {
            write_float(&mut output, 0x88 + i * 4, position[i]);
        }
        world.values[12..15].copy_from_slice(&position);
    }
    if mode & 2 != 0 {
        let mut basis = MatrixStorage {
            values: std::array::from_fn(|i| read_float(&output, 0x58 + i * 4)),
            flags: 0,
        };
        for i in [0, 1, 2, 4, 5, 6, 8, 9, 10] {
            basis.values[i] = (world.values[i] - basis.values[i]) * weight + basis.values[i];
        }
        basis = normalize_basis(basis)?;
        for i in [0, 1, 2, 4, 5, 6, 8, 9, 10] {
            write_float(&mut output, 0x58 + i * 4, basis.values[i]);
            world.values[i] = basis.values[i];
        }
    }
    if world.values.iter().any(|v| !v.is_finite()) {
        return Err("Modifier writer arithmetic overflow");
    }
    Ok(Step {
        state: output,
        world,
        effective_mode: mode,
        weight,
    })
}

#[cfg(test)]
#[path = "../../tests/unit/animation/modifier24.rs"]
mod tests;
