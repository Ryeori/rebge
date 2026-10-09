//! 140b27eb0/1436df570 reference copy/create, from explicit writer-time inputs.
//! No arithmetic, allocation address guessing or callback-input reconstruction.

#[derive(Clone, Copy)]
pub struct MatrixStorage {
    pub values: [f32; 16],
    pub flags: u32,
}

#[derive(Clone)]
pub struct ActorReferenceStorage {
    pub gao_flags: u32,
    pub world: MatrixStorage,
    pub linked_local: Option<MatrixStorage>,
    pub reference: Option<MatrixStorage>,
}

pub struct EntryContext {
    pub manager_gate: u32,
    pub clip_present: bool,
    pub actor_present: bool,
    /// Explicit pointer-identity observation; do not infer aliases from values.
    pub reference_aliases_source: bool,
}

#[derive(Debug, PartialEq)]
pub enum EntryResult {
    Skipped,
    Aliased,
    Copied,
    Created {
        native_block_size: usize,
        reference_offset: usize,
    },
}

pub fn apply(
    actor: &mut ActorReferenceStorage,
    context: &EntryContext,
) -> Result<EntryResult, &'static str> {
    if context.manager_gate == 0 || !context.clip_present || !context.actor_present {
        return Ok(EntryResult::Skipped);
    }
    let source = if actor.gao_flags & 0x400000 != 0 {
        actor
            .linked_local
            .ok_or("Linked actor entry source not captured")?
    } else {
        actor.world
    };
    if context.reference_aliases_source {
        if actor.reference.is_none() {
            return Err("Missing aliased reference storage");
        }
        return Ok(EntryResult::Aliased);
    }
    if actor.reference.is_some() {
        actor.reference = Some(source);
        return Ok(EntryResult::Copied);
    }
    if actor.gao_flags & 0x4000000 != 0 {
        return Err("Actor advertises reference but storage is missing");
    }
    let (native_block_size, reference_offset) = if actor.gao_flags & 0x10000 != 0 {
        (0xcc, 0x88)
    } else {
        (0x88, 0x44)
    };
    actor.gao_flags |= 0x4000000;
    actor.reference = Some(source);
    Ok(EntryResult::Created {
        native_block_size,
        reference_offset,
    })
}

/// Consume root effects in native order. Publication must supply the writer-time
/// actor world/local before a following ReferenceEntry reads it. The caller owns
/// clip/root sampler and context lifetimes; this does not infer them from final poses.
/// Commit only after all supported effects succeed; publication must modify only
/// its supplied storage and keep external side effects out of this transaction.
pub fn execute_effects(
    actor: &mut ActorReferenceStorage,
    effects: &[super::root_clock::RootEffect],
    mut entry_context: impl FnMut(usize, &ActorReferenceStorage) -> Result<EntryContext, &'static str>,
    mut publish: impl FnMut(usize, f32, bool, &mut ActorReferenceStorage) -> Result<(), &'static str>,
) -> Result<Vec<EntryResult>, &'static str> {
    let mut prepared = actor.clone();
    let mut entries = Vec::new();
    for effect in effects {
        match *effect {
            super::root_clock::RootEffect::ReferenceEntry { index } => {
                let context = entry_context(index, &prepared)?;
                entries.push(apply(&mut prepared, &context)?);
            }
            super::root_clock::RootEffect::Publish {
                index,
                elapsed,
                terminal,
            } => {
                publish(index, elapsed, terminal, &mut prepared)?;
            }
        }
    }
    *actor = prepared;
    Ok(entries)
}
