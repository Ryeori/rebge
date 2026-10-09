use super::*;
use serde::Deserialize;

#[derive(Deserialize)]
struct NativeCase {
    duration_byte: u8,
    elapsed_before: u16,
    delta_seconds: f32,
    actual_active: bool,
    actual_counter: u16,
    actual_ratio: f32,
}

#[test]
fn recorded_start_stop_transition_clocks() {
    // Native observed values, not Python model outputs. Source provenance
    // is retained next to this compact measurement fixture.
    let cases: Vec<NativeCase> = serde_json::from_str(include_str!(
        concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/animation/transition-clock-native.json")
    ))
    .unwrap();
    assert_eq!(cases.len(), 31);
    for case in cases {
        let result = advance_transition(
            true,
            case.duration_byte,
            case.elapsed_before,
            case.delta_seconds,
        )
        .unwrap();
        assert_eq!(result.active, case.actual_active);
        assert_eq!(result.elapsed_u16, case.actual_counter);
        if let Some(ratio) = result.downstream_ratio {
            assert_eq!(ratio.to_bits(), case.actual_ratio.to_bits());
        }
    }
}

#[test]
fn completed_or_inactive_clock_preserves_counter() {
    assert_eq!(
        advance_transition(true, 59, 11520, 0.25).unwrap(),
        TransitionStep {
            active: false,
            elapsed_u16: 11520,
            downstream_ratio: None
        }
    );
    assert_eq!(
        advance_transition(false, 59, 5153, 0.25)
            .unwrap()
            .elapsed_u16,
        5153
    );
    assert!(advance_transition(true, 59, 0, -0.01).is_err());
}

#[test]
fn saved_primary_weight_direction_and_clamping() {
    let saved = [10.0, 20.0, 30.0];
    let incoming = [0.0, 4.0, 8.0];
    assert_eq!(
        blend_saved_primary_position(saved, incoming, 0.25).unwrap(),
        [2.5, 8.0, 13.5]
    );
    assert_eq!(
        blend_saved_primary_position(saved, incoming, 2.0).unwrap(),
        saved
    );
    assert_eq!(
        blend_saved_primary_position(saved, incoming, -1.0).unwrap(),
        incoming
    );
}
