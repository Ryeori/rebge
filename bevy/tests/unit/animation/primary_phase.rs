use super::*;
use crate::animation::{
    root_clock,
    track_clock::{self, ClockState, ClockTrack},
};
#[derive(Deserialize)]
struct Case {
    before_sample: usize,
    after_sample: usize,
    track: ClockTrack,
    before: ClockState,
    after: ClockState,
    delta: f32,
    speed: u8,
    repeat_before: u8,
    repeat_after: u8,
}
#[derive(Deserialize)]
struct Fixture {
    cases: Vec<Case>,
}
#[test]
#[ignore = "Private native phase-changing capture and source action descriptors"]
fn recorded_cross_phase_carry() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../reports/jade");
    let sequence: serde_json::Value = serde_json::from_slice(
        &std::fs::read(root.join("stage43-tracking-sequence-20261008-183132.json")).unwrap(),
    )
    .unwrap();
    let actions: serde_json::Value =
        serde_json::from_slice(&std::fs::read(root.join("stage4-sally-actions.json")).unwrap())
            .unwrap();
    for (before, after, key) in [(63usize, 64usize, "7100B466"), (242, 243, "71005EAC")] {
        let a = &sequence["samples"][before];
        let b = &sequence["samples"][after];
        let action = actions["actions"]
            .as_array()
            .unwrap()
            .iter()
            .find(|a| a["key"] == key)
            .unwrap();
        let descriptor = Descriptor {
            loop_phase: action["header_byte1"].as_u64().unwrap() as u8,
            phases: action["records"]
                .as_array()
                .unwrap()
                .iter()
                .map(|r| Phase {
                    repeat_limit: r["bytes12_15"][0].as_u64().unwrap() as u8,
                    speed_source_byte: r["bytes12_15"][2].as_u64().unwrap() as u8,
                    flags: r["bytes12_15"][3].as_u64().unwrap() as u8,
                })
                .collect(),
        };
        let ta = &a["primary_clip"]["tracks"][0];
        let tb = &b["primary_clip"]["tracks"][0];
        let clock = |t: &serde_json::Value| ClockTrack {
            frames: serde_json::from_value(t["frame_headers"].clone()).unwrap(),
            flags: t["track_flags"].as_u64().unwrap() as u16,
            auxiliary_short: t["auxiliary_short_u16"].as_u64().unwrap() as u16,
        };
        let state = |t: &serde_json::Value| ClockState {
            index: t["frame_index"].as_u64().unwrap() as usize,
            elapsed: t["elapsed_seconds"].as_f64().unwrap() as f32,
            flags: t["state_flags"].as_u64().unwrap() as u16,
        };
        let header = a["primary_header_hex"].as_str().unwrap();
        let speed = u8::from_str_radix(&header[4..6], 16).unwrap();
        let result = advance_clock(
            &descriptor,
            &[clock(ta), clock(tb)],
            0,
            0,
            speed,
            state(ta),
            b["delta_time"].as_f64().unwrap() as f32,
            false,
        )
        .unwrap();
        let expected = state(tb);
        assert_eq!(
            result.phase,
            b["current_phase_index"].as_u64().unwrap() as u8
        );
        assert_eq!(
            (result.state.index, result.state.elapsed, result.state.flags),
            (expected.index, expected.elapsed, expected.flags),
            "{before} -> {after}"
        );
        assert_eq!(result.speed, 60); // The sampled header is later overwritten to56 by another writer.
        assert_eq!(result.repeat, 0);
        assert_eq!(result.remaining, 0.);
        assert_eq!(result.effects.len(), 2);
    }
}
#[test]
#[ignore = "Private native clock/repeat capture and descriptor"]
fn recorded_controller_repeats_and_root_carry() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../reports/jade");
    let fixture: Fixture = serde_json::from_slice(
        &std::fs::read(
            root.join("stage43-tracking-sequence-20261009-030317-root-clock-native.json"),
        )
        .unwrap(),
    )
    .unwrap();
    let sequence: serde_json::Value = serde_json::from_slice(
        &std::fs::read(root.join("stage43-tracking-sequence-20261009-030317.json")).unwrap(),
    )
    .unwrap();
    let native = &sequence["samples"][0]["primary_phase_descriptor"];
    let descriptor = Descriptor {
        loop_phase: native["loop_phase"].as_u64().unwrap() as u8,
        phases: native["records"]
            .as_array()
            .unwrap()
            .iter()
            .map(|r| Phase {
                repeat_limit: r["repeat_limit"].as_u64().unwrap() as u8,
                speed_source_byte: r["speed_source_byte"].as_u64().unwrap() as u8,
                flags: r["flags"].as_u64().unwrap() as u8,
            })
            .collect(),
    };
    let mut completions = 0;
    for case in fixture.cases {
        let mut state = case.before;
        let mut repeat = case.repeat_before;
        let mut delta = case.delta;
        for _ in 0..16 {
            let pass = root_clock::advance(
                &case.track,
                state,
                track_clock::scaled_delta(delta, case.speed).unwrap(),
            )
            .unwrap();
            state = pass.state;
            if !pass.finished {
                break;
            }
            let policy = complete(&descriptor, 1, repeat, false).unwrap();
            assert_eq!(policy.effect, Effect::Repeat);
            repeat = policy.repeat;
            completions += 1;
            delta = root_clock::unscaled_remaining(pass.remaining, case.speed).unwrap();
            if delta == 0. {
                break;
            }
        }
        assert_eq!(
            (state.index, state.elapsed, state.flags, repeat),
            (
                case.after.index,
                case.after.elapsed,
                case.after.flags,
                case.repeat_after
            ),
            "{} -> {}",
            case.before_sample,
            case.after_sample
        );
    }
    assert_eq!(completions, 4);
}
