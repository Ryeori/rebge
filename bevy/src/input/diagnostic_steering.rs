//! Approximate planar steering policy for the playable preview.
//! Native capture161128 shows capped turns and subsequent damping near8.1/s.
//! The VM parameters, cap writer and camera mapping are not reconstructed.
use bevy::prelude::Vec3;

pub fn turn(previous: [f32; 16], target: Vec3, delta: f32) -> f32 {
    if target.truncate().length_squared() < 1e-8 {
        return 0.;
    }
    let current = (-previous[5]).atan2(-previous[4]);
    let desired = target.y.atan2(target.x);
    let error = (desired - current + std::f32::consts::PI).rem_euclid(std::f32::consts::TAU)
        - std::f32::consts::PI;
    let dt = delta.max(0.);
    // Preview policy inferred from one trace, not a native f32 algorithm claim.
    (error * (dt * 8.1).min(1.)).clamp(-7.714286 * dt, 7.714286 * dt)
}

/// Unconnected planar adapter for experiments with native mode1 scalar yaw. Phase mapping,
/// response initialization and native optional global time scale are adapters.
pub fn slow_turn(previous: [f32; 16], target: Vec3, norm: f32,
    response: f32, delta: f32) -> crate::input::native_steering::Mode1Output {
    let current = (-previous[5]).atan2(-previous[4]);
    let desired = target.y.atan2(target.x);
    let error = if target.truncate().length_squared() < 1e-8 { 0. } else {
        (desired - current + std::f32::consts::PI).rem_euclid(std::f32::consts::TAU)
            - std::f32::consts::PI
    };
    crate::input::native_steering::mode1_yaw(crate::input::native_steering::Mode1Inputs {
        signed_angle: error, norm, previous_response1198: response, delta,
    })
}

/// Apply a rigid planar rotation about the current actor position. Rotating
/// root references about the same pivot preserves continuation without a jump.
pub fn rotate(matrix: &mut [f32; 16], pivot: [f32; 3], angle: f32) {
    let (s, c) = angle.sin_cos();
    for column in [0, 4, 8] {
        let (x, y) = (matrix[column], matrix[column + 1]);
        matrix[column] = c * x - s * y;
        matrix[column + 1] = s * x + c * y;
    }
    let (x, y) = (matrix[12] - pivot[0], matrix[13] - pivot[1]);
    matrix[12] = c * x - s * y + pivot[0];
    matrix[13] = s * x + c * y + pivot[1];
}
