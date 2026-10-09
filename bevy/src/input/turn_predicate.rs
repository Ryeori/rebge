//! Selection portion of Sally_sa_exec_demi_tour 1411daf10.
//! Caller supplies native forward/right helper results and current state.
//! Resource 26003C27 dispatch and caller scheduling are outside this function.
#[derive(Clone, Copy, Debug)]
pub struct Inputs {
    pub norm: f32,
    pub direction: [f32; 3],
    pub forward: [f32; 3],
    pub right: [f32; 3],
    pub last_action: i32,
    pub bypass_cooldown: i32,
    pub global_time: f32,
    pub time_offset: f32,
    pub last_gate_time: f32,
    pub mode: i32,
    pub speed: f32,
    pub configured_action: i32,
}

fn dot(a: [f32; 3], b: [f32; 3]) -> f32 {
    // Listing 1411db134: Y product + X product, then Z product.
    (a[1] * b[1] + a[0] * b[0]) + a[2] * b[2]
}

/// Geometry portion only; callers must qualify scheduling/state separately.
pub fn geometry_select(norm: f32, direction: [f32; 3], forward: [f32; 3],
    right: [f32; 3], configured_action: i32) -> Option<i32> {
    if norm < f32::from_bits(0x3f19999a)
        || f32::from_bits(0xbf3504f7) <= dot(forward, direction)
        || configured_action < 0 { return None; }
    if dot(right, direction) > 0. {
        match configured_action { 116 => return Some(117), 20 => return Some(118), _ => {} }
    }
    Some(configured_action)
}

pub fn select(input: Inputs) -> Option<i32> {
    if (input.last_action.wrapping_sub(26) as u32) < 2
        || input.norm < f32::from_bits(0x3f19999a)
        || (input.bypass_cooldown == 0
            && (input.global_time - input.time_offset) - input.last_gate_time
                < f32::from_bits(0x3f000000))
    {
        return None;
    }
    if f32::from_bits(0xbf3504f7) <= dot(input.forward, input.direction) {
        return None;
    }
    if input.mode < 5 && f32::from_bits(0x40200000) < input.speed {
        return Some(79);
    }
    geometry_select(input.norm, input.direction, input.forward, input.right, input.configured_action)
}

#[cfg(test)]
#[path = "../../tests/unit/input/turn_predicate.rs"]
mod tests;
