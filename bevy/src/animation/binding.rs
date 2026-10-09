//! Explicit animation-slot -> source GAO binding; 65535 is a separate root/event track.
use super::{channels::Clip, skeleton::Skeleton};
use serde::Deserialize;
use std::collections::{BTreeMap, BTreeSet};

#[derive(Deserialize)]
pub struct AnimationBinding {
    pub schema: String,
    pub object_list: String,
    pub slots: Vec<Slot>,
}

#[derive(Deserialize)]
pub struct Slot {
    pub slot: u16,
    pub gao_key: String,
}

#[derive(Debug, PartialEq)]
pub enum TrackTarget {
    Bone(usize),
    RootOrEvent,
}

impl AnimationBinding {
    pub fn resolve(&self, rig: &Skeleton) -> Result<BTreeMap<u16, usize>, &'static str> {
        if self.schema != "jade-indexed-animation-binding-v1" || self.object_list != rig.source_list
        {
            return Err("Binding schema or source object list mismatch");
        }
        rig.topological_order()?;
        let keys: BTreeMap<_, _> = rig
            .objects
            .iter()
            .enumerate()
            .map(|(i, bone)| (bone.key.as_str(), i))
            .collect();
        let mut resolved = BTreeMap::new();
        let mut used = BTreeSet::new();
        for slot in &self.slots {
            if slot.slot == u16::MAX {
                return Err("Reserved root/event slot used as bone");
            }
            let index = *keys.get(slot.gao_key.as_str()).ok_or("Unknown bound GAO")?;
            if rig.objects[index].slot != Some(usize::from(slot.slot)) {
                return Err("Skeleton and binding slot disagree");
            }
            if resolved.insert(slot.slot, index).is_some() || !used.insert(index) {
                return Err("Duplicate binding");
            }
        }
        if used.len()
            != rig
                .objects
                .iter()
                .filter(|bone| bone.slot.is_some())
                .count()
        {
            return Err("Incomplete animation binding");
        }
        Ok(resolved)
    }

    pub fn clip_targets(
        &self,
        rig: &Skeleton,
        clip: &Clip,
    ) -> Result<Vec<TrackTarget>, &'static str> {
        let resolved = self.resolve(rig)?;
        clip.tracks
            .iter()
            .map(|track| {
                if track.short1 == u16::MAX {
                    Ok(TrackTarget::RootOrEvent)
                } else {
                    Ok(TrackTarget::Bone(
                        *resolved
                            .get(&track.short1)
                            .ok_or("Unbound animation track")?,
                    ))
                }
            })
            .collect()
    }
}

#[cfg(test)]
#[path = "../../tests/unit/animation/binding.rs"]
mod tests;
