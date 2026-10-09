//! Sally140c25cc0 angular speed writer. Actor-forward and input direction
//! are explicit; alternate actor matrix context and VM writers remain external.
pub struct Inputs {
    pub gate: i32,
    pub mode: i32,
    pub input_norm: f32,
    pub stored_speed: i32,
    pub forward: [f32; 3],
    pub direction: [f32; 3],
}
pub struct Output {
    pub speed: u8,
    pub mode: i32,
    pub angle: Option<f32>,
}
/// Action binding1409ad760 uses integer scaling of descriptor byte0x22.
/// This is a different writer from Sally's rounded f32 speed calculation.
pub fn source_speed(source_byte: u8) -> u8 {
    ((source_byte as u32 * 60) >> 6) as u8
}
pub fn quantize(speed: i32) -> u8 {
    // Native CVTTSS2SI then low byte; do not collapse into integer speed*60/64.
    ((speed as f32 * 60. * f32::from_bits(0x3c800000) + 0.5) as i32) as u8
}
fn inverse_length(v: [f32; 3]) -> f32 {
    let square = v[1] * v[1] + v[0] * v[0] + v[2] * v[2];
    1. / ((square as f64).sqrt() as f32)
}
pub fn evaluate(x: &Inputs) -> Result<Output, &'static str> {
    if x.stored_speed < 0
        || !x.input_norm.is_finite()
        || x.direction.iter().chain(&x.forward).any(|v| !v.is_finite())
    {
        return Err("Invalid native angular speed inputs");
    }
    if x.gate == 0
        || x.mode > 1
        || x.input_norm == 0.
        || x.direction
            .iter()
            .all(|v| v.to_bits() & 0x7fffffff < 0x3e4cccce)
    {
        return Ok(Output {
            speed: quantize(x.stored_speed),
            mode: x.mode,
            angle: None,
        });
    }
    let a = inverse_length(x.forward);
    let b = inverse_length(x.direction);
    if !a.is_finite() || !b.is_finite() {
        return Err("Zero angular direction length");
    }
    // Listing140036c50 normalizes each component before dot, y+x+z order.
    let dot = (x.direction[1] * b) * (x.forward[1] * a)
        + (x.direction[0] * b) * (x.forward[0] * a)
        + (x.direction[2] * b) * (x.forward[2] * a);
    let angle = if dot >= 1. {
        0.
    } else if dot > -1. {
        (dot as f64).acos() as f32
    } else {
        f32::from_bits(0x40490fdb)
    };
    let mode = (angle < f32::from_bits(0x3edf65fe)) as i32 + 1;
    let argument = (f32::from_bits(0x40490fdc) - angle) * 0.5 - f32::from_bits(0x3fc90fd8);
    // std double sin/acos approximate the native CRT. One native angular event
    // matches bytes using the preceding actor world; this is not CRT bit parity.
    let speed = (((argument as f64).sin() as f32 + 1.) * x.stored_speed as f32).max(1.) as i32;
    Ok(Output {
        speed: quantize(speed),
        mode,
        angle: Some(angle),
    })
}

#[cfg(test)]
#[path = "../../tests/unit/input/animation_speed.rs"]
mod tests;
