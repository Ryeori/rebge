use super::*;
use serde::Deserialize;
#[derive(Deserialize)]
struct Case {
    before_index: usize,
    after_index: usize,
    track_index: usize,
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
#[ignore = "Private independent native ordinary track records"]
fn recorded_multitrack_ticks() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-bevy-track-clock-native.json");
    let fixture: Fixture = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let mut groups = std::collections::BTreeMap::new();
    for case in &fixture.cases {
        groups
            .entry((case.before_index, case.after_index))
            .or_insert_with(Vec::new)
            .push(case);
    }
    let mut comparisons = 0;
    for cases in groups.values() {
        let first = cases[0];
        let selected: Vec<_> = cases
            .iter()
            .map(|c| SelectedTrack {
                index: c.track_index,
                clock: &c.track,
                state: c.before,
            })
            .collect();
        let count = selected.iter().map(|t| t.index).max().unwrap() + 1;
        let result = advance(
            count,
            &selected,
            first.delta,
            first.speed,
            first.actor_root_terminal,
        )
        .unwrap();
        assert!(result.remaining.is_empty());
        for case in cases {
            let actual = result.states[case.track_index].unwrap();
            assert_eq!(
                (actual.index, actual.elapsed.to_bits(), actual.flags),
                (
                    case.after.index,
                    case.after.elapsed.to_bits(),
                    case.after.flags
                )
            );
            comparisons += 1;
        }
    }
    assert_eq!(comparisons, 5250);
    eprintln!(
        "{} native multitrack ticks; {comparisons} exact clocks",
        groups.len()
    );
}
