//! Explicit-state local channels from140b482f0/140b49fb0/140b49120.
//! Reads private exported clip JSON. Clip clocks, root references and tracking
//! remain separate; missing channels return None rather than invented poses.
use super::pose_blend::normalize_quaternion;
use serde::Deserialize;

#[derive(Clone, Deserialize)]
pub struct Clip {
    pub tracks: Vec<Track>,
}
#[derive(Clone, Deserialize)]
pub struct Track {
    pub short1: u16,
    pub frames: Vec<Frame>,
}
#[derive(Clone, Deserialize)]
pub struct Frame {
    pub tick_raw: u16,
    pub flags: u16,
    #[serde(default)]
    pub transform: Transform,
}
#[derive(Clone, Default, Deserialize)]
pub struct Transform {
    #[serde(default)]
    pub flags: u16,
    pub packed_rotation: Option<[i16; 3]>,
    pub quaternion_xyzw: Option<[f32; 4]>,
    #[serde(default)]
    pub float3_channels: Vec<[f32; 3]>,
}

pub fn packed_quaternion(packed: [i16; 3]) -> [f32; 4] {
    let [x, y, z] = packed.map(|value| f32::from(value) / 32767.0);
    let norm = (y * y + x * x) + z * z;
    let w = if norm < 1.0 { (1.0 - norm).sqrt() } else { 0.0 };
    [x, y, z, w]
}

fn key_quaternion(frame: &Frame) -> Result<Option<[f32; 4]>, &'static str> {
    if frame.transform.flags & (4 | 8 | 0x40) != 0 {
        return Err("Matrix key, remapping or alternate endpoint unsupported");
    }
    let Some(mut q) = frame
        .transform
        .packed_rotation
        .map(packed_quaternion)
        .or(frame.transform.quaternion_xyzw)
    else {
        return Ok(None);
    };
    if q.iter().any(|v| !v.is_finite()) {
        return Err("Finite quaternion key required");
    }
    if frame.flags & 0x20 != 0 {
        q[1] = -q[1];
        q[2] = -q[2];
    }
    Ok(Some(q))
}

fn endpoints(track: &Track, index: usize, elapsed: f32) -> Result<(&Frame, &Frame), &'static str> {
    if index >= track.frames.len() || !elapsed.is_finite() || elapsed < 0.0 {
        return Err("Valid forward segment state required");
    }
    Ok((
        &track.frames[index],
        &track.frames[(index + 1) % track.frames.len()],
    ))
}

pub fn sample_rotation(
    track: &Track,
    index: usize,
    elapsed: f32,
) -> Result<Option<[f32; 4]>, &'static str> {
    let (current, next) = endpoints(track, index, elapsed)?;
    let Some(a) = key_quaternion(current)? else {
        return Ok(None);
    };
    let Some(mut b) = key_quaternion(next)? else {
        return Ok(Some(a));
    };
    if current.tick_raw == 0 || current.flags & 0x800 != 0 {
        return Ok(Some(a));
    }
    let duration = f32::from(current.tick_raw) / 60.0;
    if elapsed >= duration {
        return Ok(Some(b));
    }
    let t = elapsed / duration;
    let mut dot = ((a[1] * b[1] + a[0] * b[0]) + a[2] * b[2]) + a[3] * b[3];
    if dot < 0.0 {
        dot = -dot;
        b = b.map(|v| -v);
    }
    dot = dot.min(1.0);
    if (dot - 1.0).abs() <= f32::from_bits(0x33d6bf95) {
        return Ok(Some(a));
    }
    let angle = f64::from(dot).acos() as f32;
    let inverse = 1.0 / (1.0 - dot * dot).sqrt();
    let left = f64::from((1.0 - t) * angle).sin() as f32 * inverse;
    let right = f64::from(t * angle).sin() as f32 * inverse;
    Ok(Some(normalize_quaternion(std::array::from_fn(|i| {
        a[i] * left + b[i] * right
    }))?))
}

fn points(frame: &Frame) -> Result<Vec<[f32; 3]>, &'static str> {
    let mut points = frame.transform.float3_channels.clone();
    if points.iter().flatten().any(|v| !v.is_finite()) {
        return Err("Finite curve points required");
    }
    if frame.flags & 0x20 != 0 && !points.is_empty() {
        if points.len() != 1 {
            return Err("Mirrored curve controls unsupported");
        }
        points[0][0] = -points[0][0];
    }
    Ok(points)
}

pub fn sample_translation(
    track: &Track,
    index: usize,
    elapsed: f32,
) -> Result<Option<[f32; 3]>, &'static str> {
    let (current, next) = endpoints(track, index, elapsed)?;
    if current.transform.flags & (8 | 0x40) != 0 {
        return Err("Translation remapping unsupported");
    }
    let p = points(current)?;
    if p.is_empty() {
        return Ok(None);
    }
    let next_points = points(next)?;
    if next_points.is_empty() || current.tick_raw == 0 || current.flags & 0x800 != 0 {
        return Ok(Some(p[0]));
    }
    let end = next_points[0];
    let duration = f32::from(current.tick_raw) / 60.0;
    if elapsed >= duration {
        return Ok(Some(end));
    }
    let t = elapsed / duration;
    let s = 1.0 - t;
    let result = match p.len() {
        1 => std::array::from_fn(|i| p[0][i] * s + t * end[i]),
        2 => {
            let (a, b, c) = (s * s, (t + t) * s, t * t);
            std::array::from_fn(|i| (b * p[1][i] + p[0][i] * a) + c * end[i])
        }
        3 => {
            let (a, b, c, d) = (
                (s * s) * s,
                ((s * t) * 3.0) * s,
                ((t * 3.0) * t) * s,
                (t * t) * t,
            );
            std::array::from_fn(|i| ((b * p[1][i] + p[0][i] * a) + c * p[2][i]) + d * end[i])
        }
        _ => return Err("Unsupported curve control count"),
    };
    Ok(Some(result))
}

#[cfg(test)]
#[path = "../../tests/unit/animation/channels.rs"]
mod tests;
