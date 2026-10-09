//! Sparse source-channel writes. Unwritten channels require an explicit prior
//! local pose; root reference conversion and procedural modifiers are separate.
use super::{
    binding::{AnimationBinding, TrackTarget},
    channels::{self, Clip},
    pose_blend::quaternion_matrix,
    skeleton::Skeleton,
};

#[derive(Clone, Copy)]
pub struct TrackState {
    pub index: usize,
    pub elapsed: f32,
}

#[derive(Default, Clone)]
pub struct LocalWrite {
    pub rotation: Option<[f32; 4]>,
    pub position: Option<[f32; 3]>,
}

impl LocalWrite {
    pub fn apply(&self, prior: [f32; 16]) -> Result<[f32; 16], &'static str> {
        if prior.iter().any(|v| !v.is_finite()) {
            return Err("Nonfinite prior local pose");
        }
        let mut result = prior;
        if let Some(q) = self.rotation {
            let rotation = quaternion_matrix(q);
            for i in [0, 1, 2, 4, 5, 6, 8, 9, 10] {
                result[i] = rotation[i];
            }
        }
        if let Some(p) = self.position {
            result[12..15].copy_from_slice(&p);
        }
        Ok(result)
    }
}

pub struct SampledLocalPose {
    pub writes: Vec<LocalWrite>,
    pub unsampled_tracks: Vec<usize>,
    pub root_or_event_tracks: Vec<usize>,
}

pub fn sample_local_pose(
    rig: &Skeleton,
    binding: &AnimationBinding,
    clip: &Clip,
    states: &[Option<TrackState>],
) -> Result<SampledLocalPose, &'static str> {
    if states.len() != clip.tracks.len() {
        return Err("Track state count mismatch");
    }
    let targets = binding.clip_targets(rig, clip)?;
    let mut result = SampledLocalPose {
        writes: vec![LocalWrite::default(); rig.objects.len()],
        unsampled_tracks: vec![],
        root_or_event_tracks: vec![],
    };
    for (index, ((track, state), target)) in clip.tracks.iter().zip(states).zip(targets).enumerate()
    {
        let TrackTarget::Bone(bone) = target else {
            result.root_or_event_tracks.push(index);
            continue;
        };
        let Some(state) = state else {
            result.unsampled_tracks.push(index);
            continue;
        };
        if let Some(q) = channels::sample_rotation(track, state.index, state.elapsed)? {
            result.writes[bone].rotation = Some(q);
        }
        if let Some(p) = channels::sample_translation(track, state.index, state.elapsed)? {
            result.writes[bone].position = Some(p);
        }
    }
    Ok(result)
}

#[cfg(test)]
#[path = "../../tests/unit/animation/local_pose.rs"]
mod tests;
