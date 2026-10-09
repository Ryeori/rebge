use super::*;
use serde::Deserialize;
#[derive(Deserialize)]
struct Input {
    address: u64,
    flags: u32,
    world: [f32; 16],
    world_flags: u32,
    parent: Option<u64>,
    local: Option<[f32; 16]>,
    local_flags: Option<u32>,
}
#[derive(Deserialize)]
struct Case {
    nodes: Vec<Input>,
}
#[derive(Deserialize)]
struct Fixture {
    cases: Vec<Case>,
}
#[derive(Deserialize)]
struct Mapping {
    bone_addresses: Vec<u64>,
}

#[test]
#[ignore = "Requires private final-local/native palette snapshot; not source-only playback proof"]
fn recorded_actor_attachment_to_worlds_and_palette() {
    use super::super::reference_entry::{ActorReferenceStorage, MatrixStorage};
    #[derive(Deserialize)]
    struct ExpectedPalette {
        bone: usize,
        slot: usize,
        matrix: [f32; 16],
        flags: u32,
    }
    #[derive(Deserialize)]
    struct PaletteFixture {
        actor_address: u64,
        gao_flags: u32,
        actor: Vec<f32>,
        bone_addresses: Vec<u64>,
        nodes: Vec<Input>,
        expected: Vec<ExpectedPalette>,
        expected_all: Vec<ExpectedPalette>,
        modifier_publications: Vec<ModifierInput>,
        excluded_slots: Vec<usize>,
    }
    #[derive(Deserialize)]
    struct ModifierInput {
        bone: usize,
        state_hex: String,
        world: [f32; 16],
        world_flags: u32,
    }
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let rig: Skeleton = serde_json::from_slice(
        &std::fs::read(root.join("assets/skeletons/sally/gao-parent-links.json")).unwrap(),
    )
    .unwrap();
    let fixture: PaletteFixture = serde_json::from_slice(
        &std::fs::read(
            root.join("reports/jade/stage4-sally-runtime-20261008-172956-runtime-palette.json"),
        )
        .unwrap(),
    )
    .unwrap();
    assert_eq!(fixture.excluded_slots, [27, 28]);
    assert_eq!(fixture.expected.len(), 45);
    let mut nodes: BTreeMap<_, _> = fixture
        .nodes
        .into_iter()
        .map(|n| {
            (
                n.address,
                Node {
                    flags: n.flags,
                    world: n.world,
                    world_flags: n.world_flags,
                    parent: n.parent,
                    local: n.local.map(|m| (m, n.local_flags.unwrap())),
                },
            )
        })
        .collect();
    // Deliberately perturb the prior actor root to verify that attachment
    // recomposes descendants rather than returning their cached worlds.
    nodes.get_mut(&fixture.actor_address).unwrap().world[12] += 100.;
    let prior = RuntimePose::new(&rig, fixture.bone_addresses, nodes).unwrap();
    let actor = ActorReferenceStorage {
        gao_flags: fixture.gao_flags,
        world: MatrixStorage {
            values: fixture.actor[..16].try_into().unwrap(),
            flags: fixture.actor[16] as u32,
        },
        linked_local: None,
        reference: None, // Pose attachment does not read controller reference storage.
    };
    let next = prior
        .with_actor_root(fixture.actor_address, &actor)
        .unwrap();
    assert_ne!(
        prior.nodes[&fixture.actor_address].world[12],
        next.nodes[&fixture.actor_address].world[12]
    );
    let bones: Vec<_> = fixture.expected.iter().map(|p| p.bone).collect();
    let palette = next.actor_palette(fixture.actor_address, &bones).unwrap();
    let mut maximum = 0.0_f32;
    let mut failures = Vec::new();
    for ((actual, flags), expected) in palette.into_iter().zip(fixture.expected) {
        for i in [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14] {
            let error = (actual[i] - expected.matrix[i]).abs();
            maximum = maximum.max(error);
            if error > 1e-5 {
                failures.push((expected.slot, i, error));
            }
        }
        assert_eq!(flags & 6, expected.flags & 6);
    }
    eprintln!("45 final-local -> actor/world/palette entries; max error {maximum}; failures {failures:?}");
    assert!(failures.is_empty());
    let publications: BTreeMap<_, _> = fixture
        .modifier_publications
        .iter()
        .map(|input| {
            let bytes: Vec<_> = input
                .state_hex
                .as_bytes()
                .chunks_exact(2)
                .map(|pair| u8::from_str_radix(std::str::from_utf8(pair).unwrap(), 16).unwrap())
                .collect();
            (
                input.bone,
                super::super::modifier24::LinkedPublication {
                    state: bytes.try_into().unwrap(),
                    // Conditional finalizer replay on an already finalized capture.
                    // This does not claim measured membership in the native list.
                    processed_list_member: true,
                    published_world: MatrixStorage {
                        values: input.world,
                        flags: input.world_flags,
                    },
                },
            )
        })
        .collect();
    assert_eq!(publications.len(), 2);
    let finalized = next.finalize_linked_modifiers(&publications).unwrap();
    assert_eq!(finalized.modifier_states.len(), 2);
    for (bone, input) in &publications {
        assert_eq!(finalized.modifier_states[bone], input.state);
        let address = finalized.runtime.bone_addresses[*bone];
        assert_eq!(
            finalized.runtime.nodes[&address].local,
            next.nodes[&address].local
        );
    }
    let bones: Vec<_> = fixture.expected_all.iter().map(|p| p.bone).collect();
    let palette = finalized
        .actor_palette(fixture.actor_address, &bones)
        .unwrap();
    assert_eq!(palette.len(), 47);
    let mut full_maximum = 0.0_f32;
    for ((actual, flags), expected) in palette.into_iter().zip(fixture.expected_all) {
        for i in [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14] {
            let error = (actual[i] - expected.matrix[i]).abs();
            full_maximum = full_maximum.max(error);
            assert!(
                error <= 1e-5,
                "finalized palette slot {} element {i}: {error}",
                expected.slot
            );
        }
        assert_eq!(flags & 6, expected.flags & 6);
    }
    eprintln!("47 palette entries with explicit modifier worlds; max error {full_maximum}");
}

#[test]
#[ignore = "Requires private runtime and source rig fixtures"]
fn source_clone_mapping_and_transactional_pose() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let read = |p: &str| std::fs::read(root.join(p)).unwrap();
    let rig: Skeleton =
        serde_json::from_slice(&read("assets/skeletons/sally/gao-parent-links.json")).unwrap();
    let mapping: Mapping =
        serde_json::from_slice(&read("reports/jade/stage43-bevy-runtime-bone-map.json"))
            .unwrap();
    let fixture: Fixture = serde_json::from_slice(&read(
        "reports/jade/stage43-bevy-world-hierarchy-native.json",
    ))
    .unwrap();
    let nodes: BTreeMap<_, _> = fixture
        .cases
        .into_iter()
        .next()
        .unwrap()
        .nodes
        .into_iter()
        .map(|n| {
            (
                n.address,
                Node {
                    flags: n.flags,
                    world: n.world,
                    world_flags: n.world_flags,
                    parent: n.parent,
                    local: n.local.map(|m| (m, n.local_flags.unwrap())),
                },
            )
        })
        .collect();
    let pose = RuntimePose::new(&rig, mapping.bone_addresses.clone(), nodes.clone()).unwrap();
    let bone = rig.objects.iter().position(|b| b.slot == Some(1)).unwrap();
    let old = pose.nodes[&pose.bone_addresses[bone]].local.unwrap();
    let mut prepared = old;
    prepared.0[12] += 1.;
    let next = pose
        .with_prepared_locals(&BTreeMap::from([(bone, prepared)]))
        .unwrap();
    assert_eq!(pose.nodes[&pose.bone_addresses[bone]].local.unwrap(), old);
    assert_ne!(
        pose.worlds().unwrap()[&pose.bone_addresses[bone]].0,
        next.worlds().unwrap()[&pose.bone_addresses[bone]].0
    );
    let mut aliased = mapping.bone_addresses.clone();
    aliased[1] = aliased[0];
    assert!(RuntimePose::new(&rig, aliased, nodes.clone()).is_err());
    let mut wrong = nodes;
    wrong.get_mut(&mapping.bone_addresses[bone]).unwrap().parent = Some(0);
    assert!(RuntimePose::new(&rig, mapping.bone_addresses, wrong).is_err());
    let mut invalid = prepared;
    invalid.1 |= 8;
    #[derive(Deserialize)]
    struct ChannelState {
        track_index: usize,
        index: usize,
        elapsed: f32,
    }
    #[derive(Deserialize)]
    struct LocalCase {
        slot: u16,
        channels: Vec<ChannelState>,
        observed: [f32; 16],
    }
    #[derive(Deserialize)]
    struct LocalFixture {
        source_key: String,
        cases: Vec<LocalCase>,
    }
    let binding: super::super::binding::AnimationBinding =
        serde_json::from_slice(&read("assets/skeletons/sally/animation-binding.json")).unwrap();
    let local_fixture: LocalFixture = serde_json::from_slice(&read(
        "reports/jade/stage43-bevy-walking-channels-native.json",
    ))
    .unwrap();
    let clip: super::super::channels::Clip = serde_json::from_slice(&read(&format!(
        "assets/animations/sally/local-samples/{}.json",
        local_fixture.source_key
    )))
    .unwrap();
    let slots = binding.resolve(&rig).unwrap();
    let mut count = 0;
    for case in local_fixture.cases {
        if case.slot == 0 {
            continue;
        }
        let mut states = vec![None; clip.tracks.len()];
        for state in case.channels {
            states[state.track_index] = Some(super::super::local_pose::TrackState {
                index: state.index,
                elapsed: state.elapsed,
            });
        }
        let bone = slots[&case.slot];
        let clocks: Vec<_> = clip
            .tracks
            .iter()
            .map(|t| super::super::track_clock::ClockTrack {
                frames: t
                    .frames
                    .iter()
                    .map(|f| super::super::track_clock::ClockFrame {
                        tick_raw: f.tick_raw,
                        flags: f.flags,
                    })
                    .collect(),
                flags: 2,
                auxiliary_short: 0,
            })
            .collect();
        let selected: Vec<_> = states
            .iter()
            .enumerate()
            .filter_map(|(index, state)| {
                state.map(|s| super::super::playback::SelectedTrack {
                    index,
                    clock: &clocks[index],
                    state: super::super::track_clock::ClockState {
                        index: s.index,
                        elapsed: s.elapsed,
                        flags: 0,
                    },
                })
            })
            .collect();
        let actor_address = pose.nodes[&pose.bone_addresses[slots[&0]]].parent.unwrap();
        let tick = super::super::playback::tick(
            &pose,
            &binding,
            &clip,
            &selected,
            60,
            false,
            super::super::frame::Inputs {
                rig: &rig,
                actor_address,
                actor: None,
                local_pose: None,
                ordinary_bones: &BTreeSet::from([bone]),
                root: None,
                modifiers: &BTreeMap::new(),
                modifier_requests: &[],
                delta: 0.,
                normalize_modifier_publication: false,
                palette_bones: &[bone],
            },
        )
        .unwrap();
        assert_eq!(tick.clocks.states.len(), clip.tracks.len());
        assert_eq!(tick.frame.palette.len(), 1);
        let next = tick.frame.cycle.finalized.runtime;
        let (local, flags) = next.nodes[&next.bone_addresses[bone]].local.unwrap();
        assert_ne!(flags & 4, 0);
        for i in [0, 1, 2, 4, 5, 6, 8, 9, 10] {
            assert!((local[i] - case.observed[i]).abs() <= 1e-5);
        }
        if selected.iter().any(|t| {
            super::super::channels::sample_translation(
                &clip.tracks[t.index],
                t.state.index,
                t.state.elapsed,
            )
            .unwrap()
            .is_some()
        }) {
            assert_eq!(&local[12..15], &case.observed[12..15]);
            assert_ne!(flags & 2, 0);
        }
        count += 1;
    }
    assert_eq!(count, 2720);
    let root_bone = slots[&0];
    #[derive(Deserialize)]
    struct RootCase {
        position: [f32; 3],
        rotation: [f32; 4],
        reference: [f32; 16],
        reference_flags: u32,
        actor: [f32; 16],
        actor_flags: u32,
        height: f32,
        add_height: bool,
        observed: [f32; 3],
        observed_matrix: [f32; 16],
    }
    #[derive(Deserialize)]
    struct RootFixture {
        cases: Vec<RootCase>,
    }
    let roots: RootFixture = serde_json::from_slice(&read(
        "reports/jade/stage43-bevy-actor-reference-native.json",
    ))
    .unwrap();
    let actor_address = pose.nodes[&pose.bone_addresses[root_bone]].parent.unwrap();
    assert_eq!(roots.cases.len(), 32);
    for root in roots.cases {
        let context = RootReferenceContext {
            actor_address,
            actor_matrix: root.actor,
            actor_matrix_flags: root.actor_flags,
            reference_matrix: root.reference,
            reference_flags: root.reference_flags,
            height: root.height,
            add_height: root.add_height,
        };
        let write = super::super::local_pose::LocalWrite {
            rotation: Some(root.rotation),
            position: Some(root.position),
        };
        let actor = super::super::reference_entry::ActorReferenceStorage {
            gao_flags: pose.nodes[&actor_address].flags,
            world: super::super::reference_entry::MatrixStorage {
                values: root.actor,
                flags: root.actor_flags,
            },
            linked_local: None,
            reference: None,
        };
        let frame = super::super::frame::evaluate(
            &pose,
            super::super::frame::Inputs {
                rig: &rig,
                actor_address,
                actor: Some(&actor),
                local_pose: None,
                ordinary_bones: &BTreeSet::new(),
                root: Some(super::super::frame::RootWrite {
                    bone: root_bone,
                    write: &write,
                    context: &context,
                }),
                modifiers: &BTreeMap::new(),
                modifier_requests: &[],
                delta: 0.,
                normalize_modifier_publication: false,
                palette_bones: &[root_bone],
            },
        )
        .unwrap();
        assert_eq!(frame.palette.len(), 1);
        let next = frame.cycle.finalized.runtime;
        let local = next.nodes[&next.bone_addresses[root_bone]].local.unwrap().0;
        assert_eq!(&local[12..15], &root.observed);
        for i in [0, 1, 2, 4, 5, 6, 8, 9, 10] {
            assert!((local[i] - root.observed_matrix[i]).abs() <= 1e-5);
        }
    }
    let mut forbidden = super::super::local_pose::SampledLocalPose {
        writes: vec![super::super::local_pose::LocalWrite::default(); rig.objects.len()],
        unsampled_tracks: vec![],
        root_or_event_tracks: vec![],
    };
    forbidden.writes[root_bone].position = Some([0.; 3]);
    assert!(pose
        .with_plain_channel_writes(&rig, &forbidden, &BTreeSet::from([root_bone]))
        .is_err());
    assert!(pose
        .with_prepared_locals(&BTreeMap::from([(bone, invalid)]))
        .is_err());
}
