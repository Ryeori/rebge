//! Explicit runtime hierarchy worlds. Callers must resolve clone parents,
//! root references and procedural local writes before this stage.
use super::hierarchy::{Node, compose_tracking_world};
use std::collections::BTreeMap;

pub fn compose_world_pose(
    nodes: &BTreeMap<u64, Node>,
) -> Result<BTreeMap<u64, ([f32; 16], u32)>, &'static str> {
    nodes
        .keys()
        .map(|address| Ok((*address, compose_tracking_world(nodes, *address)?)))
        .collect()
}

#[cfg(test)]
#[path = "../../tests/unit/animation/world_pose.rs"]
mod tests;
