use super::*;
use serde::Deserialize;
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
#[ignore = "Requires private measured phase repeat limit and root clocks"]
fn native_explicit_repeat_limit_continuation() {
    #[derive(Deserialize)]
    struct PhaseCase {
        before_sample: usize,
        after_sample: usize,
        track: ClockTrack,
        before: ClockState,
        after: ClockState,
        delta: f32,
        speed: u8,
        repeat_before: u8,
        repeat_after: u8,
        phase_repeat_limit: u8,
    }
    #[derive(Deserialize)]
    struct PhaseFixture {
        cases: Vec<PhaseCase>,
    }
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join(
        "../reports/jade/stage43-tracking-sequence-20261009-030317-root-clock-native.json",
    );
    let fixture: PhaseFixture = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    assert_eq!(fixture.cases.len(), 146);
    let mut entries = 0;
    for case in fixture.cases {
        let result = advance_primary_same_phase(
            &case.track,
            case.before,
            case.delta,
            case.speed,
            case.repeat_before,
            case.phase_repeat_limit,
        )
        .unwrap();
        assert!(!result.phase_finished);
        assert_eq!(result.unscaled_remaining, 0.);
        for effect in &result.effects {
            if matches!(effect, RootEffect::ReferenceEntry { .. }) {
                entries += 1;
            }
        }
        assert_eq!(
            (
                result.state.index,
                result.state.elapsed,
                result.state.flags,
                result.repeat
            ),
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
    eprintln!("146 exact same-phase clocks/repeats; {entries} reference entry intents");
    assert_eq!(entries, 4);
}

#[test]
#[ignore = "Requires private same-phase native root clocks"]
fn native_same_phase_clock_and_repeat_carry() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join(
        "../reports/jade/stage43-tracking-sequence-20261009-023957-root-clock-native.json",
    );
    let fixture: Fixture = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    assert_eq!(fixture.cases.len(), 139);
    let mut mismatches = Vec::new();
    let mut finishes = 0;
    let mut entries = Vec::new();
    let mut publications = Vec::new();
    for case in &fixture.cases {
        let mut result = advance(
            &case.track,
            case.before,
            scaled_delta(case.delta, case.speed).unwrap(),
        )
        .unwrap();
        let mut repeat = case.repeat_before;
        for _ in 0..16 {
            for effect in &result.effects {
                match *effect {
                    RootEffect::ReferenceEntry { index } => {
                        entries.push((case.after_sample, index))
                    }
                    RootEffect::Publish {
                        index,
                        elapsed,
                        terminal,
                    } => publications.push((case.after_sample, index, elapsed, terminal)),
                }
            }
            if !result.finished {
                break;
            }
            repeat = repeat.wrapping_add(1);
            finishes += 1;
            let carry = unscaled_remaining(result.remaining, case.speed).unwrap();
            if carry == 0. {
                break;
            }
            result = advance(
                &case.track,
                result.state,
                scaled_delta(carry, case.speed).unwrap(),
            )
            .unwrap();
        }
        if (
            result.state.index,
            result.state.elapsed,
            result.state.flags,
            repeat,
        ) != (
            case.after.index,
            case.after.elapsed,
            case.after.flags,
            case.repeat_after,
        ) {
            mismatches.push((
                case.before_sample,
                case.after_sample,
                result.state.index,
                result.state.elapsed,
                result.state.flags,
                repeat,
                case.after.index,
                case.after.elapsed,
                case.after.flags,
                case.repeat_after,
            ));
        }
    }
    assert_eq!(finishes, 2);
    eprintln!(
        "root cases {}, completions {finishes}, mismatches {mismatches:?}",
        fixture.cases.len()
    );
    eprintln!(
        "Numerical effect intents: entries {entries:?}; {} publications (not writer execution evidence)",
        publications.len()
    );
    assert!(mismatches.is_empty());
}
