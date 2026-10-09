//! Sally140c25cc0 moving branch; stationary predicates remain explicit.
/// Ordinary 141013870 mode2 high bins; run/side gates are caller inputs.
/// Saved Ghidra and the 20261010 held-run/start recordings independently
/// expose brain1C/20/24=3 and brain28=2; low bins are unchanged.
pub fn ordinary_action_table(mut mode1: [i32; 12], run_mode: bool) -> [i32; 12] {
    if run_mode {
        mode1[6..9].fill(3);
        mode1[9] = 2;
    }
    mode1
}
pub struct StationaryInputs {
    pub mode: i32,
    pub pending: i32,
    pub last_action: i32,
    pub selected_action: i32,
    pub scene_time: f32,
    pub time_origin: f32,
    pub interaction_time: f32,
    pub action_time: f32,
    pub idle: i32,
    pub waiting: i32,
    pub primary_disabled: bool,
    pub blend_active: bool,
    pub exception: bool,
}
pub struct StationaryDecision {
    pub requested: Option<i32>,
    pub consume_pending: bool,
}
/// Stationary branch of 140c25cc0; caller supplies value < 0.35.
/// Brain writes, actor direction reset and action-table dispatch are separate.
pub fn stationary_action(x: &StationaryInputs) -> StationaryDecision {
    let mut result = StationaryDecision {
        requested: None,
        consume_pending: false,
    };
    if x.blend_active && !x.primary_disabled && !x.exception {
        return result;
    }
    let now = x.scene_time - x.time_origin;
    if now - x.interaction_time >= 2. || x.mode > 2 {
        if x.pending == 0 || x.mode > 2 {
            if x.last_action != x.selected_action || x.primary_disabled {
                result.requested = Some(if now - x.action_time >= 2. {
                    x.waiting
                } else {
                    x.idle
                });
            }
        } else {
            result.requested = Some(x.pending);
            result.consume_pending = true;
        }
    } else {
        result.requested = Some(0x6e);
    }
    if x.last_action == 0x17 && !x.primary_disabled && x.mode < 3 {
        result.requested = None;
    }
    result
}
pub fn moving_action(
    value: f32,
    actions: &[i32; 12],
    blend_active: bool,
    primary_disabled: bool,
    exception: bool,
) -> Result<Option<i32>, &'static str> {
    if !value.is_finite() || value < 0.35 {
        return Err("Stationary selector predicates required");
    }
    if blend_active && !primary_disabled && !exception {
        return Ok(None);
    }
    if value > 0.925 {
        return Ok(Some(actions[9]));
    }
    let mut threshold = 0.421875f32;
    let mut index = 1;
    while threshold < value {
        threshold += f32::from_bits(0x3d933334);
        index += 1;
        if index >= actions.len() {
            return Err("Selector bins exceeded action table");
        }
    }
    Ok(Some(actions[index]))
}
/// 1560e4150 scalar branch with normal-mode gate and special action supplied.
pub fn joy_norm(
    previous: f32,
    target: f32,
    delta: f32,
    normal_mode: bool,
    special_action: bool,
) -> Result<f32, &'static str> {
    if !previous.is_finite() || !target.is_finite() || !delta.is_finite() || delta < 0. {
        return Err("Invalid joy norm input");
    }
    if target == 0. || !normal_mode {
        return Ok(target);
    }
    if special_action {
        return Ok(0.35);
    }
    if previous <= target {
        let next = delta * f32::from_bits(0x40366666) + previous;
        Ok(if next > target {
            target
        } else if next < 0.35 {
            0.35
        } else {
            next
        })
    } else {
        let next = previous - delta * f32::from_bits(0x40366666);
        Ok(if next > 1. {
            1.
        } else if next < target {
            target
        } else {
            next
        })
    }
}

#[cfg(test)]
#[path = "../../tests/unit/input/animation_selector.rs"]
mod tests;
