//! Actor-relative palette from explicit post-procedural world matrices.
//! Bone/bind composition and vertex deformation are separate stages.
use super::{actor_reference::inverse_no_scale, hierarchy::affine_product};

pub fn palette_matrix(
    actor: [f32; 16],
    actor_flags: u32,
    bone_world: [f32; 16],
    bone_flags: u32,
) -> Result<([f32; 16], u32), &'static str> {
    let (inverse, flags) = inverse_no_scale(actor, actor_flags)?;
    affine_product(&bone_world, &inverse, bone_flags, flags)
}

#[cfg(test)]
#[path = "../../tests/unit/animation/skin_palette.rs"]
mod tests;
