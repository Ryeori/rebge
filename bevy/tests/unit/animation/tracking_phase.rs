use super::*;
use serde::Deserialize;

#[derive(Deserialize)]
struct NativePhase {
    before_counter: u8,
    delta: f32,
    primary_flags: Option<u8>,
    active_slots: u8,
    transition_flags: Option<u8>,
    control: u16,
    observed_counter: u8,
}

#[test]
fn recorded_primary_and_transition_counters() {
    let cases: Vec<NativePhase> = serde_json::from_str(include_str!(
        concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/animation/tracking-phase-native.json")
    ))
    .unwrap();
    assert_eq!(cases.len(), 148);
    for case in cases {
        let result = tracking_phase_gate(
            case.before_counter,
            0.5,
            case.delta,
            case.primary_flags,
            case.active_slots,
            case.transition_flags,
            case.control,
        )
        .unwrap();
        assert_eq!(result.counter, case.observed_counter);
    }
}

#[test]
fn transition_phase_is_distinct_from_primary() {
    let blocked = tracking_phase_gate(0, 1.0, 0.0, Some(4), 3, Some(0), 0x1000).unwrap();
    assert!(!blocked.continue_tracking);
    let absent = tracking_phase_gate(9, 1.0, 0.0, Some(0), 3, None, 0).unwrap();
    assert_eq!(absent.counter, 0);
    assert!(absent.continue_tracking);
}

#[test]
fn time_ramp_and_call_count_stop_at_native_boundaries() {
    let ramp = tracking_phase_gate(15, 0.5, 1.0 / 60.0, Some(0), 1, None, 0x8000).unwrap();
    assert_eq!(
        ramp,
        PhaseGate {
            counter: 16,
            strength: 1.0,
            continue_tracking: false
        }
    );
    let calls = tracking_phase_gate(5, 1.0, 0.0, Some(0), 1, None, 0).unwrap();
    assert_eq!(
        calls,
        PhaseGate {
            counter: 6,
            strength: 0.4,
            continue_tracking: false
        }
    );
}
