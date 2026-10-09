use super::*;
use serde::Deserialize;

#[derive(Deserialize)]
struct Case {
    before: usize,
    after: usize,
    state_hex: String,
    nominal: [f32; 16],
    nominal_flags: u32,
    parent: [f32; 16],
    parent_flags: u32,
    delta: f32,
    observed_position: [f32; 3],
    observed_world: [f32; 16],
}
#[derive(Deserialize)]
struct Fixture {
    cases: Vec<Case>,
}

#[test]
#[ignore = "Requires private conditional adjacent modifier inputs; not callback chronology proof"]
fn recorded_completed_cycle_lag_positions_and_bases() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join(
        "../reports/jade/stage43-tracking-sequence-20261008-173533-modifier24-step-native.json",
    );
    let fixture: Fixture = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    assert_eq!(fixture.cases.len(), 139);
    let mut maximum_raw = 0.0_f32;
    let mut maximum_normalized = 0.0_f32;
    for case in fixture.cases {
        let bytes: Vec<_> = case
            .state_hex
            .as_bytes()
            .chunks_exact(2)
            .map(|pair| u8::from_str_radix(std::str::from_utf8(pair).unwrap(), 16).unwrap())
            .collect();
        let state: State = bytes.try_into().unwrap();
        let result = step(
            &state,
            MatrixStorage {
                values: case.nominal,
                flags: case.nominal_flags,
            },
            Some(MatrixStorage {
                values: case.parent,
                flags: case.parent_flags,
            }),
            case.delta,
        )
        .unwrap();
        assert_eq!(result.effective_mode & 10, 8);
        for i in 0..3 {
            assert_eq!(
                read_float(&result.state, 0x88 + i * 4).to_bits(),
                case.observed_position[i].to_bits(),
                "lag pair {} -> {} component {i}",
                case.before,
                case.after
            );
        }
        let normalized = normalize_basis(result.world).unwrap();
        for i in [0, 1, 2, 4, 5, 6, 8, 9, 10] {
            let raw_error = (result.world.values[i] - case.observed_world[i]).abs();
            let normalized_error = (normalized.values[i] - case.observed_world[i]).abs();
            maximum_raw = maximum_raw.max(raw_error);
            maximum_normalized = maximum_normalized.max(normalized_error);
            assert!(
                raw_error <= 1e-5,
                "raw basis pair {} -> {} element {i}: {raw_error}",
                case.before,
                case.after
            );
            assert!(
                normalized_error <= 1e-5,
                "normalized basis pair {} -> {} element {i}: {normalized_error}",
                case.before,
                case.after
            );
        }
    }
    eprintln!("139 conditional lag positions exact; raw basis max {maximum_raw}; normalized basis max {maximum_normalized}");
}
