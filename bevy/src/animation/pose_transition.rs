//! Explicit two-instance ordinary local blend before procedural writers.
use super::{
    local_pose::SampledLocalPose, pose_blend::blend_local_no_scale, runtime_pose::RuntimePose,
    skeleton::Skeleton,
};
use std::collections::{BTreeMap, BTreeSet};

/// Native ratio moves from outgoing transition pose (0) to new primary (1).
/// Each sparse pose uses the supplied prior local for its unwritten channels.
/// Slot0 and actor destinations require their separate reference contexts.
pub fn apply(
    prior: &RuntimePose,
    rig: &Skeleton,
    outgoing: &SampledLocalPose,
    primary: &SampledLocalPose,
    bones: &BTreeSet<usize>,
    ratio: f32,
) -> Result<RuntimePose, &'static str> {
    if !ratio.is_finite() || !(0.0..=1.0).contains(&ratio) {
        return Err("Invalid transition ratio");
    }
    let a = prior.with_plain_channel_writes(rig, outgoing, bones)?;
    let b = prior.with_plain_channel_writes(rig, primary, bones)?;
    let mut writes = BTreeMap::new();
    for bone in bones {
        let wa = &outgoing.writes[*bone];
        let wb = &primary.writes[*bone];
        if wa.rotation.is_none()
            && wa.position.is_none()
            && wb.rotation.is_none()
            && wb.position.is_none()
        {
            continue;
        }
        let address = prior.bone_addresses[*bone];
        let (incoming, aflags) = a.nodes[&address].local.ok_or("Missing outgoing local")?;
        let (saved, bflags) = b.nodes[&address].local.ok_or("Missing primary local")?;
        let matrix = blend_local_no_scale(incoming, aflags, saved, bflags, ratio)?;
        writes.insert(*bone, (matrix, (aflags | bflags | 6) & !8));
    }
    prior.with_prepared_locals(&writes)
}

#[cfg(test)]
#[path = "../../tests/unit/animation/pose_transition.rs"]
mod tests;
