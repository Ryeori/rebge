use super::*;
use serde::Deserialize;

#[derive(Deserialize)]
struct TrackInput {
    source: Track,
    clock: ClockTrack,
    state: ClockState,
}
#[derive(Deserialize)]
struct Case {
    sample: usize,
    tracks: Vec<TrackInput>,
    gao_flags: u32,
    actor: Vec<f32>,
    reference: Vec<f32>,
    entry_gate: u32,
}
#[derive(Deserialize)]
struct Fixture {
    cases: Vec<Case>,
    evaluation_reference: Vec<f32>,
}

#[test]
#[ignore = "Private standing-turn post-frame root relations; not full pose or selection proof"]
fn recorded_standing_turn_root_publication() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../reports/jade");
    let mut checked = 0;
    for (stamp, key) in [("171809", "26003A85"), ("182845", "26003A36")] {
        let path = root.join(format!(
            "stage43-tracking-sequence-20261009-{stamp}-root-pipeline.json"
        ));
        let raw: serde_json::Value =
            serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
        for value in raw["cases"].as_array().unwrap() {
            if value["source_key"].as_str() != Some(key) {
                continue;
            }
            let case: Case = serde_json::from_value(value.clone()).unwrap();
            let mut actor = ActorReferenceStorage {
                gao_flags: case.gao_flags,
                world: MatrixStorage {
                    values: case.actor[..16].try_into().unwrap(),
                    flags: case.actor[16] as u32,
                },
                linked_local: None,
                reference: Some(MatrixStorage {
                    values: case.reference[..16].try_into().unwrap(),
                    flags: case.reference[16] as u32,
                }),
            };
            for input in &case.tracks {
                actor = run_track(
                    &input.clock,
                    &input.source,
                    input.state,
                    0.,
                    &actor,
                    &EntryContext {
                        manager_gate: case.entry_gate,
                        clip_present: true,
                        actor_present: true,
                        reference_aliases_source: false,
                    },
                    &PublicationContext {
                        reference: ReferenceSource::Actor,
                        root_count: case.tracks.len() as u32,
                        dispatch_flags: 0,
                    },
                )
                .unwrap()
                .actor;
            }
            for i in [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14] {
                assert!(
                    (actor.world.values[i] - case.actor[i]).abs() <= 1e-5,
                    "sample{} element{i}",
                    case.sample
                );
            }
            checked += 1;
        }
    }
    assert_eq!(checked, 15);
}

#[test]
#[ignore = "Private independent reverse-input recordings; zero-delta relation only"]
fn recorded_reverse_root_publication() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../reports/jade");
    let mut checked = 0;
    let mut maximum = 0.0_f32;
    for name in ["171056", "171809", "201330", "201452", "201905", "213501"] {
        let path = root.join(format!(
            "stage43-tracking-sequence-20261009-{name}-root-pipeline.json"
        ));
        let raw: serde_json::Value =
            serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
        for value in raw["cases"].as_array().unwrap() {
            if !matches!(
                value["source_key"].as_str().unwrap(),
                "7100B589" | "7100B58B" | "7100B5E5" | "7100B5E7" | "9E0004DD" | "9E0004DE"
            ) {
                continue;
            }
            let case: Case = serde_json::from_value(value.clone()).unwrap();
            let mut actor = ActorReferenceStorage {
                gao_flags: case.gao_flags,
                world: MatrixStorage {
                    values: case.actor[..16].try_into().unwrap(),
                    flags: case.actor[16] as u32,
                },
                linked_local: None,
                reference: Some(MatrixStorage {
                    values: case.reference[..16].try_into().unwrap(),
                    flags: case.reference[16] as u32,
                }),
            };
            for input in &case.tracks {
                let result = run_track(
                    &input.clock,
                    &input.source,
                    input.state,
                    0.,
                    &actor,
                    &EntryContext {
                        manager_gate: case.entry_gate,
                        clip_present: true,
                        actor_present: true,
                        reference_aliases_source: false,
                    },
                    &PublicationContext {
                        reference: ReferenceSource::Actor,
                        root_count: case.tracks.len() as u32,
                        dispatch_flags: 0,
                    },
                )
                .unwrap();
                assert!(result.entries.is_empty());
                actor = result.actor;
            }
            for i in [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14] {
                let error = (actor.world.values[i] - case.actor[i]).abs();
                maximum = maximum.max(error);
                assert!(
                    error <= 1e-5,
                    "sequence{name} sample{} element{i}: {error}",
                    case.sample
                );
            }
            checked += 1;
        }
    }
    assert_eq!(checked, 191);
    eprintln!("Reverse root publication: {checked} cases, max error {maximum}");
}

#[test]
#[ignore = "Private independent running recordings; zero-delta relation only"]
fn recorded_run_root_publication() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../reports/jade");
    let mut checked = 0;
    let mut maximum = 0.0_f32;
    for name in ["182845", "183348"] {
        let path = root.join(format!(
            "stage43-tracking-sequence-20261009-{name}-root-pipeline.json"
        ));
        let raw: serde_json::Value =
            serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
        for value in raw["cases"].as_array().unwrap() {
            if !matches!(value["source_key"].as_str().unwrap(), "7100B0E9") {
                continue;
            }
            let case: Case = serde_json::from_value(value.clone()).unwrap();
            let mut actor = ActorReferenceStorage {
                gao_flags: case.gao_flags,
                world: MatrixStorage {
                    values: case.actor[..16].try_into().unwrap(),
                    flags: case.actor[16] as u32,
                },
                linked_local: None,
                reference: Some(MatrixStorage {
                    values: case.reference[..16].try_into().unwrap(),
                    flags: case.reference[16] as u32,
                }),
            };
            for input in &case.tracks {
                let result = run_track(
                    &input.clock,
                    &input.source,
                    input.state,
                    0.,
                    &actor,
                    &EntryContext {
                        manager_gate: case.entry_gate,
                        clip_present: true,
                        actor_present: true,
                        reference_aliases_source: false,
                    },
                    &PublicationContext {
                        reference: ReferenceSource::Actor,
                        root_count: case.tracks.len() as u32,
                        dispatch_flags: 0,
                    },
                )
                .unwrap();
                assert!(result.entries.is_empty());
                actor = result.actor;
            }
            for i in [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14] {
                let error = (actor.world.values[i] - case.actor[i]).abs();
                maximum = maximum.max(error);
                assert!(
                    error <= 1e-5,
                    "sequence{name} sample{} element{i}: {error}",
                    case.sample
                );
            }
            checked += 1;
        }
    }
    assert_eq!(checked, 49);
    eprintln!("Run root publication: {checked} cases, max error {maximum}");
}

#[test]
#[ignore = "Private slow-stick recording; restart root relation only"]
fn recorded_restart_both_phases_publication() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../reports/jade");
    let mut checked = 0;
    let mut maximum = 0.0_f32;
    for name in ["185743"] {
        let path = root.join(format!(
            "stage43-tracking-sequence-20261009-{name}-root-pipeline.json"
        ));
        let raw: serde_json::Value =
            serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
        for value in raw["cases"].as_array().unwrap() {
            if !matches!(
                value["source_key"].as_str().unwrap(),
                "7100B2E4" | "9E0004E6"
            ) {
                continue;
            }
            let case: Case = serde_json::from_value(value.clone()).unwrap();
            let mut actor = ActorReferenceStorage {
                gao_flags: case.gao_flags,
                world: MatrixStorage {
                    values: case.actor[..16].try_into().unwrap(),
                    flags: case.actor[16] as u32,
                },
                linked_local: None,
                reference: Some(MatrixStorage {
                    values: case.reference[..16].try_into().unwrap(),
                    flags: case.reference[16] as u32,
                }),
            };
            for input in &case.tracks {
                let result = run_track(
                    &input.clock,
                    &input.source,
                    input.state,
                    0.,
                    &actor,
                    &EntryContext {
                        manager_gate: case.entry_gate,
                        clip_present: true,
                        actor_present: true,
                        reference_aliases_source: false,
                    },
                    &PublicationContext {
                        reference: ReferenceSource::Actor,
                        root_count: case.tracks.len() as u32,
                        dispatch_flags: 0,
                    },
                )
                .unwrap();
                assert!(result.entries.is_empty());
                actor = result.actor;
            }
            for i in [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14] {
                let error = (actor.world.values[i] - case.actor[i]).abs();
                maximum = maximum.max(error);
                assert!(
                    error <= 1e-5,
                    "sequence{name} sample{} element{i}: {error}",
                    case.sample
                );
            }
            checked += 1;
        }
    }
    assert_eq!(checked, 37);
    eprintln!("Restart root publication: {checked} cases, max error {maximum}");
}

#[test]
#[ignore = "Requires private post-frame zero-delta numerical fixture, not frame replay proof"]
fn recorded_zero_delta_direct_publication_relation() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-tracking-sequence-20261009-030317-root-pipeline.json");
    let fixture: Fixture = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    assert_eq!(fixture.cases.len(), 185);
    let mut maximum = 0.0_f32;
    let mut refresh_maximum = 0.0_f32;
    for case in fixture.cases {
        let mut actor = ActorReferenceStorage {
            gao_flags: case.gao_flags,
            world: MatrixStorage {
                values: case.actor[..16].try_into().unwrap(),
                flags: case.actor[16] as u32,
            },
            linked_local: None,
            reference: Some(MatrixStorage {
                values: case.reference[..16].try_into().unwrap(),
                flags: case.reference[16] as u32,
            }),
        };
        let saved_actor = actor.clone();
        assert_eq!(case.tracks.len(), 2);
        for input in &case.tracks {
            let execution = run_track(
                &input.clock,
                &input.source,
                input.state,
                0.,
                &actor,
                &EntryContext {
                    manager_gate: case.entry_gate,
                    clip_present: true,
                    actor_present: true,
                    reference_aliases_source: false,
                },
                // Explicit enabled-publication numerical hypothesis. These
                // suppressor inputs were not captured at callback time.
                &PublicationContext {
                    reference: ReferenceSource::Actor,
                    root_count: 2,
                    dispatch_flags: 0,
                },
            )
            .unwrap();
            assert!(execution.entries.is_empty());
            assert!(!execution.pass.finished);
            assert_eq!(execution.pass.state.index, input.state.index);
            assert_eq!(
                execution.pass.state.elapsed.to_bits(),
                input.state.elapsed.to_bits()
            );
            actor = execution.actor;
        }
        for i in [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14] {
            let error = (actor.world.values[i] - case.actor[i]).abs();
            maximum = maximum.max(error);
            assert!(error <= 1e-5, "sample {} element {i}: {error}", case.sample);
        }
        assert_eq!(actor.world.flags, case.actor[16] as u32);
        let refresh = evaluate_refresh(
            &saved_actor,
            &case
                .tracks
                .iter()
                .map(|t| RefreshTrack {
                    clock: &t.clock,
                    source: &t.source,
                    state: t.state,
                })
                .collect::<Vec<_>>(),
            MatrixStorage {
                values: fixture.evaluation_reference[..16].try_into().unwrap(),
                flags: fixture.evaluation_reference[16] as u32,
            },
            2,
            0,
        )
        .unwrap();
        assert_eq!(refresh.states.len(), 2);
        for i in 0..16 {
            let error = (refresh.reference.values[i] - case.reference[i]).abs();
            refresh_maximum = refresh_maximum.max(error);
            assert!(
                error <= 1e-5,
                "refresh sample {} element {i}: {error}",
                case.sample
            );
        }
        assert_eq!(refresh.reference.flags, case.reference[16] as u32);
    }
    eprintln!("185 zero-delta direct publications; maximum error {maximum}");
    eprintln!(
        "185 conditional zero-delta reference evaluations; maximum error {refresh_maximum}"
    );
}
