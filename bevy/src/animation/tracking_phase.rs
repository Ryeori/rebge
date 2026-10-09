//! Resolved phase gate from1409b3c55..1409b3e11.
//! This gate precedes tracking angles; it does not prove the writer executed.

#[derive(Debug, PartialEq)]
pub struct PhaseGate {
    pub counter: u8,
    pub strength: f32,
    pub continue_tracking: bool,
}

pub fn tracking_phase_gate(
    counter: u8,
    strength: f32,
    delta: f32,
    current_flags: Option<u8>,
    component_high_byte: u8,
    transition_flags: Option<u8>,
    phase_control: u16,
) -> Result<PhaseGate, &'static str> {
    if !strength.is_finite() || !delta.is_finite() || delta < 0.0 {
        return Err("Finite forward tracking phase input required");
    }
    let blocked = current_flags.is_some_and(|primary| {
        let primary_blocked = primary & 4 == 0;
        if component_high_byte == 1 {
            primary_blocked
        } else {
            transition_flags.is_some_and(|flags| primary_blocked || flags & 4 == 0)
        }
    });
    if !blocked {
        return Ok(PhaseGate {
            counter: 0,
            strength,
            continue_tracking: true,
        });
    }
    if phase_control & 0x8000 != 0 {
        if counter >= 16 {
            return Ok(PhaseGate {
                counter: 16,
                strength,
                continue_tracking: false,
            });
        }
        let increment = (delta / f32::from_bits(0x3c888888) + 0.5).trunc();
        if !increment.is_finite() || increment >= 2147483648.0 {
            return Err("Tracking delta outside native integer conversion range");
        }
        let counter = counter.wrapping_add((increment as u32 & 255) as u8);
        return Ok(PhaseGate {
            counter,
            strength: f32::from(counter) * 0.0625,
            continue_tracking: counter < 16,
        });
    }
    if phase_control & 0x1000 != 0 {
        return Ok(PhaseGate {
            counter,
            strength,
            continue_tracking: false,
        });
    }
    if counter >= 6 {
        return Ok(PhaseGate {
            counter: 6,
            strength,
            continue_tracking: false,
        });
    }
    let counter = counter + 1;
    Ok(PhaseGate {
        counter,
        strength: 0.4,
        continue_tracking: counter < 6,
    })
}

#[cfg(test)]
#[path = "../../tests/unit/animation/tracking_phase.rs"]
mod tests;
