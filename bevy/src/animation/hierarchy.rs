//! Jade linked target hierarchy (140b33020 / no-scale 140ae9c00).
//! This numerical core does not read native pointers or drive ECS bones.
use std::collections::{BTreeMap, BTreeSet};

pub const IDENTITY: [f32; 16] = [
    1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.,
];

/// 1409b4e70 follows bit400000 (distinct from target-position bit1).
/// Accumulate child-to-root in native order; root world is an explicit input.
pub fn compose_tracking_world(
    nodes: &BTreeMap<u64, Node>,
    address: u64,
) -> Result<([f32; 16], u32), &'static str> {
    let mut current = address;
    let mut seen = BTreeSet::new();
    let mut path = Vec::new();
    loop {
        if seen.len() >= 64 || !seen.insert(current) {
            return Err("Cyclic or overlong world hierarchy");
        }
        let node = nodes.get(&current).ok_or("Missing world hierarchy node")?;
        if node.flags & 0x400000 == 0 {
            break;
        }
        let parent = node.parent.ok_or("Unknown linked parent")?;
        if parent == 0 {
            break;
        }
        path.push(current);
        current = parent;
    }
    let root = &nodes[&current];
    if path.is_empty() {
        return Ok((root.world, root.world_flags));
    }
    let (mut matrix, mut flags) = (IDENTITY, 0);
    for child in path {
        let (local, local_flags) = nodes[&child]
            .local
            .as_ref()
            .ok_or("Missing linked local matrix")?;
        (matrix, flags) = affine_product(&matrix, local, flags, *local_flags)?;
    }
    affine_product(&matrix, &root.world, flags, root.world_flags)
}

#[derive(Clone, Debug)]
pub struct Node {
    pub flags: u32,
    pub world: [f32; 16],
    pub world_flags: u32,
    pub parent: Option<u64>,
    pub local: Option<([f32; 16], u32)>,
}

pub fn affine_product(
    local: &[f32; 16],
    parent: &[f32; 16],
    local_flags: u32,
    parent_flags: u32,
) -> Result<([f32; 16], u32), &'static str> {
    if (local_flags | parent_flags) & 8 != 0 {
        return Err("Scaled branch is not reconstructed");
    }
    if local.iter().chain(parent.iter()).any(|v| !v.is_finite()) {
        return Err("Nonfinite matrix");
    }
    let mut result = IDENTITY;
    for column in [0, 4, 8, 12] {
        for row in 0..3 {
            let a = local[column] * parent[row];
            let b = local[column + 1] * parent[4 + row];
            let c = local[column + 2] * parent[8 + row];
            let sum = (a + b) + c;
            result[column + row] = if column == 12 {
                sum + parent[12 + row]
            } else {
                sum
            };
        }
    }
    let mut flags = (local_flags | parent_flags) & 4;
    if result[12..15].iter().any(|v| *v != 0.) {
        flags |= 2;
    }
    Ok((result, flags))
}

pub fn linked_target_position(
    nodes: &BTreeMap<u64, Node>,
    address: u64,
) -> Result<[f32; 3], &'static str> {
    if address == 0 {
        return Ok([0.; 3]);
    }
    let mut current = address;
    let mut path = Vec::new();
    let mut seen = BTreeSet::new();
    let root = loop {
        if seen.len() >= 64 || !seen.insert(current) {
            return Err("Cyclic or overlong hierarchy");
        }
        let node = nodes.get(&current).ok_or("Missing hierarchy node")?;
        if node.flags & 1 == 0 {
            break current;
        }
        match node.parent.ok_or("Unknown parent")? {
            0 => {
                path.clear();
                break address;
            }
            parent => {
                path.push(current);
                current = parent;
            }
        }
    };
    let root_node = nodes.get(&root).ok_or("Missing root")?;
    if path.is_empty() {
        return Ok(root_node.world[12..15].try_into().unwrap());
    }
    let (mut accumulated, mut flags) = (IDENTITY, 0);
    for child in path {
        let node = &nodes[&child];
        if node.flags & 0x400000 == 0 {
            return Err("Absent local matrix branch");
        }
        let (local, local_flags) = node.local.as_ref().ok_or("Missing local matrix")?;
        (accumulated, flags) = affine_product(&accumulated, local, flags, *local_flags)?;
    }
    let (world, _) = affine_product(&accumulated, &root_node.world, flags, root_node.world_flags)?;
    Ok(world[12..15].try_into().unwrap())
}

#[cfg(test)]
#[path = "../../tests/unit/animation/hierarchy.rs"]
mod tests;
