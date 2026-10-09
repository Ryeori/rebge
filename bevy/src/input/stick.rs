//! Native global-joy component gate and ordinary magnitude saturation.
use bevy::prelude::Vec2;

// 140d01870..140d01898: clear sign, compare bits, accept if any component
// is strictly greater than 0x3eb33333. Device normalization remains unresolved.
pub(crate) const MOVEMENT_DEADZONE: f32 = f32::from_bits(0x3eb33333);
const FULL_STICK_THRESHOLD: f32 = f32::from_bits(0x3f6ccccd);

pub(crate) fn movement_stick(value: Vec2) -> Vec2 {
    if value.is_finite()
        && (value.x.abs() > MOVEMENT_DEADZONE || value.y.abs() > MOVEMENT_DEADZONE)
    {
        // 140d01a62..140d01ae5: f32 square sum, f64 sqrt rounded to f32,
        // then saturate to unit magnitude strictly above native0.925.
        let square_sum = value.x * value.x + value.y * value.y;
        let length = (f64::from(square_sum).sqrt()) as f32;
        if length > FULL_STICK_THRESHOLD {
            value * (1. / length)
        } else {
            value
        }
    } else {
        Vec2::ZERO
    }
}

#[cfg(test)]
#[path = "../../tests/unit/input/stick.rs"]
mod tests;
