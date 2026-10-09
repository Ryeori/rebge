//! CPU vertex consumer140a41f90; packed weight words retain their low vertex bits.
use super::{
    hierarchy::{affine_product, IDENTITY},
    reference_entry::MatrixStorage,
};
use serde::Deserialize;
#[derive(Deserialize)]
pub struct Record {
    pub palette_index: usize,
    pub bind: [f32; 16],
    pub bind_flags: u32,
    pub words: Vec<u32>,
    pub mirror: bool,
}
#[derive(Deserialize)]
pub struct Deformation {
    pub positions: Vec<[f32; 3]>,
    pub records: Vec<Record>,
    pub vertex_indices: Vec<usize>,
    pub rigid_slot: Option<usize>,
}
fn effective(m: [f32; 16], flags: u32) -> Result<[f32; 16], &'static str> {
    if flags & 8 != 0 {
        return Err("Scaled bind composition unsupported");
    }
    let mut out = IDENTITY;
    if flags & 4 != 0 {
        for i in [0, 1, 2, 4, 5, 6, 8, 9, 10] {
            out[i] = m[i];
        }
    }
    if flags & 2 != 0 {
        out[12..15].copy_from_slice(&m[12..15]);
    }
    Ok(out)
}
pub fn compose(record: &Record, bone: MatrixStorage) -> Result<MatrixStorage, &'static str> {
    let mut bind = record.bind;
    if record.mirror {
        for i in [0, 4, 8, 12] {
            bind[i] = -bind[i];
        }
    }
    let (values, flags) = affine_product(
        &effective(bind, record.bind_flags)?,
        &effective(bone.values, bone.flags)?,
        record.bind_flags,
        bone.flags,
    )?;
    Ok(MatrixStorage { values, flags })
}
fn transform(p: [f32; 3], m: MatrixStorage) -> [f32; 3] {
    std::array::from_fn(|axis| {
        let value = if m.flags & 4 != 0 {
            let p = if m.flags & 8 != 0 {
                std::array::from_fn(|j| p[j] * m.values[j * 4 + 3])
            } else {
                p
            };
            (p[1] * m.values[4 + axis] + p[0] * m.values[axis]) + p[2] * m.values[8 + axis]
        } else if m.flags & 8 != 0 {
            p[axis] * m.values[axis * 4 + 3]
        } else {
            p[axis]
        };
        if m.flags & 2 != 0 {
            value + m.values[12 + axis]
        } else {
            value
        }
    })
}
pub fn deform(
    data: &Deformation,
    palette: &[([f32; 16], u32)],
) -> Result<Vec<[f32; 3]>, &'static str> {
    if data.positions.iter().flatten().any(|v| !v.is_finite()) {
        return Err("Nonfinite source vertex");
    }
    let matrix = |index: usize| -> Result<MatrixStorage, &'static str> {
        let (values, flags) = *palette.get(index).ok_or("Missing skin palette entry")?;
        if values.iter().any(|v| !v.is_finite()) {
            return Err("Nonfinite skin matrix");
        }
        Ok(MatrixStorage { values, flags })
    };
    let mut output = vec![[0.; 3]; data.positions.len()];
    if let Some(index) = data.rigid_slot {
        if !data.records.is_empty() {
            return Err("Mixed rigid and weighted deformation");
        }
        let m = matrix(index)?;
        for (o, p) in output.iter_mut().zip(&data.positions) {
            *o = transform(*p, m);
        }
    } else {
        for record in &data.records {
            let m = compose(record, matrix(record.palette_index)?)?;
            for word in &record.words {
                let weight = f32::from_bits(*word);
                let index = (*word & 0xffff) as usize;
                if !weight.is_finite() {
                    return Err("Nonfinite skin weight");
                }
                let p = *data
                    .positions
                    .get(index)
                    .ok_or("Skin vertex index out of range")?;
                let value = transform(p, m);
                for axis in 0..3 {
                    output[index][axis] = value[axis] * weight + output[index][axis];
                }
            }
        }
    }
    if output.iter().flatten().any(|v| !v.is_finite()) {
        return Err("Skin arithmetic overflow");
    }
    data.vertex_indices
        .iter()
        .map(|i| {
            output
                .get(*i)
                .copied()
                .ok_or("Triangle skin index out of range")
        })
        .collect()
}

#[cfg(test)]
#[path = "../../tests/unit/animation/skin.rs"]
mod tests;
