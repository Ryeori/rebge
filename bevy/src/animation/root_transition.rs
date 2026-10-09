//! Reference-converted slot0 operands blend before hierarchy/procedural writers.
use super::{
    local_pose::LocalWrite,
    pose_blend::blend_local_no_scale,
    runtime_pose::{RootReferenceContext, RuntimePose},
    skeleton::Skeleton,
};
use std::collections::BTreeMap;
pub struct Outgoing<'a> {
    pub write: &'a LocalWrite,
    pub context: &'a RootReferenceContext,
    pub ratio: f32,
}
pub fn apply(
    prior: &RuntimePose,
    rig: &Skeleton,
    bone: usize,
    primary: &LocalWrite,
    context: &RootReferenceContext,
    outgoing: Option<Outgoing<'_>>,
) -> Result<RuntimePose, &'static str> {
    let primary_pose = prior.with_reference_root_write(rig, bone, primary, context)?;
    let Some(outgoing) = outgoing else {
        return Ok(primary_pose);
    };
    if outgoing.context.actor_address != context.actor_address
        || outgoing.context.actor_matrix != context.actor_matrix
        || outgoing.context.actor_matrix_flags != context.actor_matrix_flags
    {
        return Err("Root transition operands require a shared actor publication");
    }
    if !outgoing.ratio.is_finite() || !(0.0..=1.0).contains(&outgoing.ratio) {
        return Err("Invalid root transition ratio");
    }
    let outgoing_pose =
        prior.with_reference_root_write(rig, bone, outgoing.write, outgoing.context)?;
    let address = prior.bone_addresses[bone];
    let (a, aflags) = outgoing_pose.nodes[&address]
        .local
        .ok_or("Missing outgoing root local")?;
    let (b, bflags) = primary_pose.nodes[&address]
        .local
        .ok_or("Missing primary root local")?;
    let blended = blend_local_no_scale(a, aflags, b, bflags, outgoing.ratio)?;
    primary_pose.with_prepared_locals(&BTreeMap::from([(
        bone,
        (blended, (aflags | bflags | 6) & !8),
    )]))
}

#[cfg(test)]
#[path = "../../tests/unit/animation/root_transition.rs"]
mod tests;
