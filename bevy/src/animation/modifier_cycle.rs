//! Parent-first modifier24 cycle with explicit runtime records and request order.
//! Native pointer/list bytes are opaque; logical processed order is kept separately.
use super::{
    hierarchy::affine_product, modifier24, reference_entry::MatrixStorage,
    runtime_pose::RuntimePose,
};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone)]
pub struct Record {
    pub state: modifier24::State,
    pub record_flags: u32,
}
pub struct Cycle {
    pub finalized: super::runtime_pose::FinalizedPose,
    pub records: BTreeMap<usize, Record>,
    pub evaluation_order: Vec<usize>,
    pub finalization_order: Vec<usize>,
}

fn mode(state: &modifier24::State) -> u32 {
    u32::from_le_bytes(state[4..8].try_into().unwrap())
}
fn copy_fields(
    target: &mut modifier24::State,
    source: &modifier24::State,
    fields: &[(usize, usize)],
) {
    for (offset, size) in fields {
        target[*offset..offset + size].copy_from_slice(&source[*offset..offset + size]);
    }
}
fn eligible(record: &Record) -> bool {
    record.record_flags & 0xa000000 == 0 && record.record_flags & 0x1000000 != 0
}

struct Working {
    pose: RuntimePose,
    records: BTreeMap<usize, Record>,
    worlds: BTreeMap<u64, ([f32; 16], u32)>,
    indices: BTreeMap<u64, usize>,
    visiting: BTreeSet<usize>,
    order: Vec<usize>,
    scratch: Option<modifier24::State>,
    publications: BTreeMap<usize, modifier24::LinkedPublication>,
    delta: f32,
    normalize_publication: bool,
}

impl Working {
    fn evaluate(&mut self, bone: usize) -> Result<(), &'static str> {
        if self.visiting.len() >= 64 || !self.visiting.insert(bone) {
            return Err("Modifier parent recursion is cyclic or excessive");
        }
        let result = self.evaluate_inner(bone);
        self.visiting.remove(&bone);
        result
    }
    fn evaluate_inner(&mut self, bone: usize) -> Result<(), &'static str> {
        let address = *self
            .pose
            .bone_addresses
            .get(bone)
            .ok_or("Unknown modifier bone")?;
        let record = self
            .records
            .get(&bone)
            .ok_or("Missing requested modifier record")?
            .clone();
        if !eligible(&record) {
            return Ok(());
        }
        let node = self
            .pose
            .nodes
            .get(&address)
            .ok_or("Missing modifier runtime node")?
            .clone();
        if node.flags & 0x400000 == 0 {
            return Err("Cycle currently supports linked modifier actors");
        }
        let (mut local, mut local_flags) = node.local.ok_or("Missing modifier local")?;
        // Native backs up parameters even when this node has already been processed.
        self.scratch = Some(record.state);
        let mut prepared = modifier24::save_prepare_inputs(
            &record.state,
            MatrixStorage {
                values: local,
                flags: local_flags,
            },
        );
        self.records.get_mut(&bone).unwrap().state = prepared;
        if mode(&record.state) & 0x10000000 != 0 {
            if !self.order.contains(&bone) {
                return Err("Input contains an unfinished external modifier cycle");
            }
            return Ok(());
        }
        let parent_address = node
            .parent
            .filter(|p| *p != 0)
            .ok_or("Linked modifier parent missing")?;
        let parent_node = self
            .pose
            .nodes
            .get(&parent_address)
            .ok_or("Unknown modifier parent")?
            .clone();
        if parent_node.flags & 0x2000 != 0 {
            if let Some(parent_bone) = self.indices.get(&parent_address).copied() {
                if self.records.get(&parent_bone).is_some_and(eligible) {
                    self.evaluate(parent_bone)?;
                }
            }
        }
        let scratch = self.scratch.ok_or("Missing modifier inheritance scratch")?;
        let mut inherited_mode = mode(&prepared);
        // Decompiled `(char)mode < 0` is bit7, not bit31.
        if inherited_mode & 0x80 != 0 {
            inherited_mode = mode(&scratch);
            prepared[4..8].copy_from_slice(&inherited_mode.to_le_bytes());
        }
        if inherited_mode & 0x100 != 0 {
            copy_fields(&mut prepared, &scratch, &[(8, 4), (0xd8, 4), (0xec, 4)]);
        }
        if inherited_mode & 0x800 != 0 {
            copy_fields(&mut prepared, &scratch, &[(0xa8, 12), (0xb4, 12)]);
        }
        let (parent_world, parent_flags) = *self
            .worlds
            .get(&parent_address)
            .ok_or("Missing parent writer world")?;
        let parent_local = if parent_node.flags & 0x400000 != 0 {
            self.pose.nodes[&parent_address]
                .local
                .ok_or("Missing linked parent local")?
        } else {
            (parent_world, parent_flags)
        };
        if inherited_mode & 0x10 != 0 && parent_node.flags & 0x400000 != 0 {
            local[12..15].copy_from_slice(&parent_local.0[12..15]);
        }
        if inherited_mode & 0x20 != 0 {
            for i in [0, 1, 2, 4, 5, 6, 8, 9, 10] {
                local[i] = parent_local.0[i];
            }
        }
        if inherited_mode & 0x40 != 0 {
            if parent_local.1 & 8 != 0 {
                return Err("Inherited scale path unsupported");
            }
            local_flags &= !8;
        }
        // Native saves local after inheritance; retain parameter backups from entry.
        for (i, value) in local.iter().enumerate() {
            prepared[0xc + i * 4..0x10 + i * 4].copy_from_slice(&value.to_le_bytes());
        }
        prepared[0x4c..0x50].copy_from_slice(&local_flags.to_le_bytes());
        let (nominal, nominal_flags) =
            affine_product(&local, &parent_world, local_flags, parent_flags)?;
        let evaluation = modifier24::evaluate_prepared_linked(
            &prepared,
            MatrixStorage {
                values: nominal,
                flags: nominal_flags,
            },
            MatrixStorage {
                values: parent_world,
                flags: parent_flags,
            },
            self.delta,
        )?;
        self.pose = self
            .pose
            .with_linked_modifier_evaluation(bone, &evaluation)?;
        let published = if self.normalize_publication {
            modifier24::normalize_basis(evaluation.step.world)?
        } else {
            evaluation.step.world
        };
        self.worlds
            .insert(address, (published.values, published.flags));
        let mut state = evaluation.step.state;
        let processed_mode = mode(&state) | 0x10000000;
        state[4..8].copy_from_slice(&processed_mode.to_le_bytes());
        state[0xa0..0xa8].copy_from_slice(&address.to_le_bytes());
        self.records.get_mut(&bone).unwrap().state = state;
        self.publications.insert(
            bone,
            modifier24::LinkedPublication {
                state,
                processed_list_member: true,
                published_world: published,
            },
        );
        self.order.push(bone);
        Ok(())
    }
}

/// Complete supported linked modifier cycle. Records/request order come from
/// the caller; absence of a configured record means no parent modifier here.
/// Normalization is an explicit publication policy, separate from the writer.
pub fn run(
    pose: &RuntimePose,
    records: &BTreeMap<usize, Record>,
    requests: &[usize],
    delta: f32,
    normalize_publication: bool,
) -> Result<Cycle, &'static str> {
    let mut working = Working {
        pose: RuntimePose {
            bone_addresses: pose.bone_addresses.clone(),
            nodes: pose.nodes.clone(),
        },
        records: records.clone(),
        worlds: pose.worlds()?,
        indices: pose
            .bone_addresses
            .iter()
            .enumerate()
            .map(|(i, a)| (*a, i))
            .collect(),
        visiting: BTreeSet::new(),
        order: Vec::new(),
        scratch: None,
        publications: BTreeMap::new(),
        delta,
        normalize_publication,
    };
    for bone in requests {
        working.evaluate(*bone)?;
    }
    // Repeated prepare calls can overwrite parameter backups in native state.
    for (bone, publication) in &mut working.publications {
        publication.state = working.records[bone].state;
    }
    let finalized = working
        .pose
        .finalize_linked_modifiers(&working.publications)?;
    for (bone, state) in &finalized.modifier_states {
        working.records.get_mut(bone).unwrap().state = *state;
    }
    let finalization_order = working.order.iter().rev().copied().collect();
    Ok(Cycle {
        finalized,
        records: working.records,
        evaluation_order: working.order,
        finalization_order,
    })
}

#[cfg(test)]
#[path = "../../tests/unit/animation/modifier_cycle.rs"]
mod tests;
