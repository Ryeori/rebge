//! Readable source rig topology. Source flags are not live clone flags.
use serde::Deserialize;
use std::collections::BTreeMap;

#[derive(Deserialize)]
pub struct Skeleton {
    pub source_list: String,
    pub objects: Vec<Bone>,
}

#[derive(Deserialize)]
pub struct Bone {
    pub slot: Option<usize>,
    pub key: String,
    pub flags: String,
    pub gao_matrix: [f32; 16],
    pub linked_gao: Option<String>,
    pub linked_matrix: Option<[f32; 16]>,
    pub linked_matrix_flags: Option<u32>,
}

impl Skeleton {
    /// Parent-before-child indices for each component, with all links checked.
    pub fn topological_order(&self) -> Result<Vec<usize>, &'static str> {
        let mut keys = BTreeMap::new();
        let mut slots = BTreeMap::new();
        for (index, bone) in self.objects.iter().enumerate() {
            if keys.insert(bone.key.as_str(), index).is_some() {
                return Err("Duplicate GAO key");
            }
            if let Some(slot) = bone.slot {
                if slots.insert(slot, index).is_some() {
                    return Err("Duplicate animation slot");
                }
            }
            if u32::from_str_radix(&bone.flags, 16).is_err() {
                return Err("Invalid source flags");
            }
            if bone
                .gao_matrix
                .iter()
                .chain(bone.linked_matrix.iter().flatten())
                .any(|v| !v.is_finite())
            {
                return Err("Nonfinite source matrix");
            }
            if bone.linked_gao.is_some()
                && (bone.linked_matrix.is_none() || bone.linked_matrix_flags.is_none())
            {
                return Err("Incomplete source link");
            }
        }
        let mut marks = vec![0u8; self.objects.len()];
        let mut output = Vec::new();
        fn visit(
            index: usize,
            rig: &Skeleton,
            keys: &BTreeMap<&str, usize>,
            marks: &mut [u8],
            output: &mut Vec<usize>,
        ) -> Result<(), &'static str> {
            match marks[index] {
                2 => return Ok(()),
                1 => return Err("Cyclic source hierarchy"),
                _ => {}
            }
            marks[index] = 1;
            if let Some(parent) = rig.objects[index].linked_gao.as_ref() {
                visit(
                    *keys.get(parent.as_str()).ok_or("Missing parent GAO")?,
                    rig,
                    keys,
                    marks,
                    output,
                )?;
            }
            marks[index] = 2;
            output.push(index);
            Ok(())
        }
        for index in 0..self.objects.len() {
            visit(index, self, &keys, &mut marks, &mut output)?;
        }
        Ok(output)
    }
}

#[cfg(test)]
#[path = "../../tests/unit/animation/skeleton.rs"]
mod tests;
