use super::*;
#[derive(Deserialize)]
struct Case {
    track: ClockTrack,
    before: ClockState,
    after: ClockState,
    delta: f32,
    speed: u8,
    actor_root_terminal: bool,
}
#[derive(Deserialize)]
struct Fixture {
    cases: Vec<Case>,
}
#[test]
#[ignore = "Requires private measured ordinary clock fixture"]
fn native_forward_states_and_speed_byte() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-bevy-track-clock-native.json");
    let fixture: Fixture = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    assert_eq!(fixture.cases.len(), 5250);
    for case in fixture.cases {
        let result = advance(
            &case.track,
            case.before,
            scaled_delta(case.delta, case.speed).unwrap(),
            case.actor_root_terminal,
        )
        .unwrap();
        assert_eq!(result.state.index, case.after.index);
        assert_eq!(result.state.elapsed, case.after.elapsed);
        assert_eq!(result.state.flags, case.after.flags);
    }
}
#[test]
fn outgoing_boundary_hold_and_root_finish() {
    let track = ClockTrack {
        frames: vec![
            ClockFrame {
                tick_raw: 1,
                flags: 128,
            },
            ClockFrame {
                tick_raw: 1,
                flags: 128,
            },
        ],
        flags: 2,
        auxiliary_short: 0,
    };
    let state = ClockState {
        index: 0,
        elapsed: 0.,
        flags: 1,
    };
    let result = advance(&track, state, 1. / 60., false).unwrap();
    assert_eq!(result.state.index, 0);
    assert_eq!(result.state.elapsed, 1. / 60.);
    let result = advance(&track, state, 1., true).unwrap();
    assert!(result.finished);
    assert_eq!(result.state.index, 1);
    assert!(result.remaining > 0.9);
}
