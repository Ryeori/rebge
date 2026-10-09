use super::*;
use serde::Deserialize;
#[derive(Deserialize)]
struct State {
    track_index: usize,
    index: usize,
    elapsed: f32,
}
#[derive(Deserialize)]
struct Case {
    slot: u16,
    channels: Vec<State>,
    observed: [f32; 16],
}
#[derive(Deserialize)]
struct Fixture {
    source_key: String,
    cases: Vec<Case>,
}

#[test]
#[ignore = "Requires private source rig and native walking fixture"]
fn assembled_writes_match_native_walking_and_preserve_unwritten_channels() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let read = |p: &str| std::fs::read(root.join(p)).unwrap();
    let rig: Skeleton =
        serde_json::from_slice(&read("assets/skeletons/sally/gao-parent-links.json")).unwrap();
    let binding: AnimationBinding =
        serde_json::from_slice(&read("assets/skeletons/sally/animation-binding.json")).unwrap();
    let fixture: Fixture = serde_json::from_slice(&read(
        "reports/jade/stage43-bevy-walking-channels-native.json",
    ))
    .unwrap();
    let clip: Clip = serde_json::from_slice(&read(&format!(
        "assets/animations/sally/local-samples/{}.json",
        fixture.source_key
    )))
    .unwrap();
    let slots = binding.resolve(&rig).unwrap();
    assert_eq!(fixture.cases.len(), 2880);
    for case in fixture.cases {
        let mut states = vec![None; clip.tracks.len()];
        for state in case.channels {
            states[state.track_index] = Some(TrackState {
                index: state.index,
                elapsed: state.elapsed,
            });
        }
        let clocks: Vec<_> = clip
            .tracks
            .iter()
            .map(|track| super::super::track_clock::ClockTrack {
                frames: track
                    .frames
                    .iter()
                    .map(|frame| super::super::track_clock::ClockFrame {
                        tick_raw: frame.tick_raw,
                        flags: frame.flags,
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
                state.map(|state| super::super::playback::SelectedTrack {
                    index,
                    clock: &clocks[index],
                    state: super::super::track_clock::ClockState {
                        index: state.index,
                        elapsed: state.elapsed,
                        flags: 0,
                    },
                })
            })
            .collect();
        let playback =
            super::super::playback::sample(&rig, &binding, &clip, &selected, 0., 60, false)
                .unwrap();
        assert_eq!(playback.clocks.states.len(), clip.tracks.len());
        let pose = playback.locals;
        let write = &pose.writes[slots[&case.slot]];
        assert!(write.rotation.is_some());
        let matrix = write.apply(super::super::hierarchy::IDENTITY).unwrap();
        for i in [0, 1, 2, 4, 5, 6, 8, 9, 10] {
            assert!((matrix[i] - case.observed[i]).abs() <= 1e-5);
        }
        if case.slot != 0 && write.position.is_some() {
            assert_eq!(&matrix[12..15], &case.observed[12..15]);
        }
        assert!(!pose.unsampled_tracks.is_empty());
    }
    let mut prior = super::super::hierarchy::IDENTITY;
    prior[12..15].copy_from_slice(&[7., 8., 9.]);
    let rotation_only = LocalWrite {
        rotation: Some([0., 0., 0., 1.]),
        position: None,
    };
    assert_eq!(&rotation_only.apply(prior).unwrap()[12..15], &[7., 8., 9.]);
    assert_eq!(LocalWrite::default().apply(prior).unwrap(), prior);
}
