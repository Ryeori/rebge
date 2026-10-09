//! Finite ordinary-heading arithmetic from Sally's native heading callback.
//!
//! Provenance: reports/ghidra/raw/agent-jade-heading-factor-listing-20261009.json
//! (14110d853..14110d87f), heading listing and constants in the same directory.
//! The caller supplies native runtime planar velocity and previous actor10D0
//! response. Input-filter scheduling, actor mode and world/root application are
//! outside this helper; a preview velocity estimate is not a native fixture.

#[derive(Clone, Copy, Debug)]
pub struct Inputs {
    /// Native runtime X/Y velocity, rather than the requested stick direction.
    pub runtime_velocity: [f32; 2],
    /// Previous actor10D0 value, retained by the caller between updates.
    pub response: f32,
    pub delta: f32,
}

#[derive(Clone, Copy, Debug)]
pub struct Output {
    pub response: f32,
    /// Bounded interpolation factor consumed by the direction-blend helper.
    pub factor: f32,
}

/// Ordinary finite-input path. Exceptional native SSE NaN behavior is excluded.
pub fn step(input: Inputs) -> Output {
    let alpha = (input.delta * 5.).clamp(0., 1.);
    let response = (1. - alpha) * input.response + alpha * 3.;
    let [vx, vy] = input.runtime_velocity;
    // Keep native Y product + X product + zero, then double sqrt -> float.
    let squared_speed = (vy * vy + vx * vx) + 0.;
    let speed = (f64::from(squared_speed).sqrt()) as f32;
    let speed_gain = speed.max(3.).min(4.5);
    let factor = ((speed_gain * response) * f32::from_bits(0x3cf5c28f))
        * (input.delta * 30.);
    Output { response, factor: factor.clamp(0., 1.) }
}

#[derive(Clone, Copy, Debug)]
pub struct Mode1Inputs {
    /// Signed planar angle supplied by the caller; angle extraction is separate.
    pub signed_angle: f32,
    /// Nonnegative native input norm.
    pub norm: f32,
    /// Previous actor1198 response, retained between updates.
    pub previous_response1198: f32,
    pub delta: f32,
}

#[derive(Clone, Copy, Debug)]
pub struct Mode1Output {
    pub updated_response: f32,
    pub yaw: f32,
}

/// Finite mode1 direct-yaw arithmetic from 14110d470.
/// Provenance: agent-jade-heading-direct-yaw-branch-listing-20261010.json
/// and agent-jade-heading-direct-yaw-writer-listing-20261010.json in
/// reports/ghidra/raw. Optional global time scaling in 140b33710 is excluded:
/// the caller must establish that bound before applying this yaw. Caller gates,
/// angle extraction, banked modes and matrix writes are not part of this helper.
pub fn mode1_yaw(input: Mode1Inputs) -> Mode1Output {
    let alpha = (input.delta * 5.).clamp(0., 1.);
    let updated_response = (1. - alpha) * input.previous_response1198 + alpha * 1.;
    let sign = if input.signed_angle < 0. { -1. } else { 1. };
    let min_abs_angle = input.signed_angle.abs().min(input.norm / 3.5);
    let angle_part = (sign * min_abs_angle) * 0.9;
    let time_part = (input.delta * 30.) * updated_response;
    Mode1Output { updated_response, yaw: angle_part * time_part }
}

#[cfg(test)]
#[path = "../../tests/unit/input/native_steering.rs"]
mod tests;
