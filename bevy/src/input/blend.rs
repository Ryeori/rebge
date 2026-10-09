//! Recovered input blend from the Sally controller callback.
//! Rate 12.0 is read from the user's binary through Ghidra (stage4-motion-constants.json).
//! Native delta-time0.0166015625/0.017578125 reproduces three recorded vector
//! updates bit-for-bit. Capture adjacency is not atomic callback-entry proof.
use bevy::prelude::Vec3;

pub fn blend_direction(previous: Vec3, target: Vec3, delta: f32) -> Vec3 {
    let alpha = (delta * 12.0).clamp(0.0, 1.0);
    target * alpha + previous * (1.0 - alpha)
}

#[cfg(test)]
#[path = "../../tests/unit/input/blend.rs"]
mod tests;
