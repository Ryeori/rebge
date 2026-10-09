//! Selected pose stages in explicit order. Controller/VM inputs remain caller-owned.
use super::{
    local_pose::{LocalWrite, SampledLocalPose},
    modifier_cycle::{self, Cycle, Record},
    reference_entry::ActorReferenceStorage,
    runtime_pose::{RootReferenceContext, RuntimePose},
    skeleton::Skeleton,
};
use std::collections::{BTreeMap, BTreeSet};

pub struct RootWrite<'a> {
    pub bone: usize,
    pub write: &'a LocalWrite,
    pub context: &'a RootReferenceContext,
}
pub struct Inputs<'a> {
    pub rig: &'a Skeleton,
    pub actor_address: u64,
    pub actor: Option<&'a ActorReferenceStorage>,
    pub local_pose: Option<&'a SampledLocalPose>,
    pub ordinary_bones: &'a BTreeSet<usize>,
    pub root: Option<RootWrite<'a>>,
    pub modifiers: &'a BTreeMap<usize, Record>,
    pub modifier_requests: &'a [usize],
    pub delta: f32,
    pub normalize_modifier_publication: bool,
    pub palette_bones: &'a [usize],
}
pub struct Frame {
    pub cycle: Cycle,
    pub palette: Vec<([f32; 16], u32)>,
}

/// Transactional actor publication -> sparse locals -> reference root ->
/// modifier cycle -> palette. Returned runtime and modifier records feed the
/// next frame; palette uses retained publications after local restoration.
pub fn evaluate(prior: &RuntimePose, inputs: Inputs<'_>) -> Result<Frame, &'static str> {
    if !inputs.delta.is_finite() || inputs.delta < 0. {
        return Err("Invalid frame delta");
    }
    let mut pose = RuntimePose {
        bone_addresses: prior.bone_addresses.clone(),
        nodes: prior.nodes.clone(),
    };
    if let Some(actor) = inputs.actor {
        pose = pose.with_actor_root(inputs.actor_address, actor)?;
    }
    if let Some(locals) = inputs.local_pose {
        pose = pose.with_plain_channel_writes(inputs.rig, locals, inputs.ordinary_bones)?;
    } else if !inputs.ordinary_bones.is_empty() {
        return Err("Eligible ordinary bones require sampled channels");
    }
    if let Some(root) = inputs.root {
        if root.context.actor_address != inputs.actor_address {
            return Err("Root frame actor mismatch");
        }
        let actor = pose
            .nodes
            .get(&inputs.actor_address)
            .ok_or("Missing frame actor")?;
        if actor.world != root.context.actor_matrix
            || actor.world_flags != root.context.actor_matrix_flags
        {
            return Err("Root reference context differs from frame actor publication");
        }
        pose = pose.with_reference_root_write(inputs.rig, root.bone, root.write, root.context)?;
    }
    let cycle = modifier_cycle::run(
        &pose,
        inputs.modifiers,
        inputs.modifier_requests,
        inputs.delta,
        inputs.normalize_modifier_publication,
    )?;
    let palette = cycle
        .finalized
        .actor_palette(inputs.actor_address, inputs.palette_bones)?;
    Ok(Frame { cycle, palette })
}
