//! Forward transition clock (1409bcd20) and root position blend (15358c6f0).
//! f32 operations preserve the observed quantization and operand direction.

#[derive(Debug, PartialEq)]
pub struct TransitionStep {
    pub active: bool,
    pub elapsed_u16: u16,
    pub downstream_ratio: Option<f32>,
}

pub fn advance_transition(
    active: bool,
    duration_byte: u8,
    elapsed_u16: u16,
    delta_seconds: f32,
) -> Result<TransitionStep, &'static str> {
    if !delta_seconds.is_finite() || delta_seconds < 0.0 {
        return Err("Transition requires finite forward time");
    }
    let unchanged = TransitionStep {
        active: false,
        elapsed_u16,
        downstream_ratio: None,
    };
    if !active {
        return Ok(unchanged);
    }
    let duration = (f32::from(duration_byte) + 1.0) / 60.0;
    let elapsed = f32::from(elapsed_u16) / 15360.0 + delta_seconds;
    if duration <= elapsed {
        // Native clears the active bit without replacing the old counter/ratio.
        return Ok(unchanged);
    }
    Ok(TransitionStep {
        active: true,
        elapsed_u16: ((elapsed * 15360.0).trunc() as u32 & 0xffff) as u16,
        downstream_ratio: Some(elapsed / duration),
    })
}

pub fn blend_saved_primary_position(
    saved_primary: [f32; 3],
    incoming: [f32; 3],
    ratio: f32,
) -> Result<[f32; 3], &'static str> {
    if !ratio.is_finite()
        || saved_primary
            .iter()
            .chain(&incoming)
            .any(|v| !v.is_finite())
    {
        return Err("Position blend requires finite inputs");
    }
    let weight = ratio.clamp(0.0, 1.0);
    let complement = 1.0 - weight;
    Ok(std::array::from_fn(|i| {
        complement * incoming[i] + saved_primary[i] * weight
    }))
}

#[cfg(test)]
#[path = "../../tests/unit/animation/transition.rs"]
mod tests;
