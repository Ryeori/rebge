//! 1554d4620 / 1409ad760 / 1554cb7f0: explicit progress remap and seek.
use super::track_clock::{ClockState, ClockTrack};

pub fn progress(track: &ClockTrack, state: ClockState) -> Result<(f32, f32), &'static str> {
    if state.index >= track.frames.len() || !state.elapsed.is_finite() {
        return Err("Invalid progress input");
    }
    let mut before = 0f32;
    for frame in &track.frames[..state.index] {
        before = f32::from(frame.tick_raw) / 60. + before;
    }
    let mut total = before;
    for frame in &track.frames[state.index..] {
        total = f32::from(frame.tick_raw) / 60. + total;
    }
    Ok((state.elapsed + before, total))
}
pub fn remap(
    elapsed: f32,
    duration: f32,
    target_duration: f32,
    flags: u8,
) -> Result<f32, &'static str> {
    if duration <= 0.
        || !elapsed.is_finite()
        || !duration.is_finite()
        || !target_duration.is_finite()
    {
        return Err("Invalid action progress duration");
    }
    let ratio = elapsed / duration;
    Ok(if flags & 1 != 0 { ratio } else { 1. - ratio } * target_duration)
}
pub fn seek(
    track: &ClockTrack,
    seconds: f32,
    prior_flags: u16,
) -> Result<ClockState, &'static str> {
    if track.frames.is_empty()
        || !seconds.is_finite()
        || seconds < 0.
        || seconds * 60. >= i32::MAX as f32
    {
        return Err("Unsupported action seek time");
    }
    let mut ticks = (seconds * 60.) as i32 as u16;
    let quantized = f32::from(ticks) / 60.;
    let mut index = 0;
    for frame in &track.frames {
        if ticks < frame.tick_raw {
            return Ok(ClockState {
                index,
                elapsed: f32::from(ticks) / 60. + (seconds - quantized),
                flags: prior_flags | 4,
            });
        }
        ticks = ticks.wrapping_sub(frame.tick_raw);
        index += 1;
    }
    Ok(ClockState {
        index: track.frames.len() - 1,
        elapsed: 0.,
        flags: prior_flags | 4,
    })
}

#[cfg(test)]
#[path = "../../tests/unit/animation/action_progress.rs"]
mod tests;
