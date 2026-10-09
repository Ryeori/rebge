use super::*;

#[test]
#[ignore = "Private independent geometry-qualified original ramps"]
fn recorded_slow_ramp_can_select_turn() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/movement-suite/native-dynamics-turn-audit-20261009.json");
    let fixture: serde_json::Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let mut selected_slow = 0;
    let mut rejected_after_turn = 0;
    for run in fixture["runs"].as_array().unwrap() {
        if run["case"].as_str() != Some("standing_right_rise_0.70") { continue; }
        for row in run["rows"].as_array().unwrap() {
            assert_eq!(row["ordinary_forward"], true);
            if row["norm"].as_f64().unwrap() < 0.6 { continue; }
            let vector = |key: &str| {
                let values = row[key].as_array().unwrap();
                std::array::from_fn(|i| values[i].as_f64().unwrap() as f32)
            };
            let selected = select(Inputs {
                norm: row["norm"].as_f64().unwrap() as f32,
                direction: vector("direction"), forward: vector("forward"), right: vector("right"),
                last_action: row["last_action"].as_i64().unwrap() as i32,
                bypass_cooldown: row["bypass_cooldown"].as_i64().unwrap() as i32,
                global_time: row["cooldown_age"].as_f64().unwrap() as f32,
                time_offset: 0., last_gate_time: 0.,
                mode: row["mode"].as_i64().unwrap() as i32,
                speed: row["speed"].as_f64().unwrap() as f32,
                configured_action: row["configured_action"].as_i64().unwrap() as i32,
            });
            // Observed 116 still retains last_action=1 at its entry. This
            // checks independent measured inputs, not callback chronology.
            if row["action"].as_i64() == Some(116)
                && row["last_action"].as_i64() == Some(1)
            {
                assert_eq!(selected, Some(116));
                selected_slow += 1;
            } else if row["action"].as_i64() == Some(1)
                && row["diagnostic_forward_dot"].as_f64().unwrap() > 0.9
            {
                assert_eq!(selected, None);
                rejected_after_turn += 1;
            }
        }
    }
    assert!(selected_slow > 0 && rejected_after_turn > 0);
}

#[test]
#[ignore = "Private independent original standing ramps"]
fn recorded_fast_medium_and_slow_gate_inputs() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/movement-suite/native-standing-qualified-controls-20261009.json");
    let fixture: serde_json::Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let mut accepted = 0;
    let mut rejected_slow = 0;
    for run in fixture["runs"].as_array().unwrap() {
        let slow = run["case"].as_str().unwrap().ends_with("0.70");
        for row in run["rows"].as_array().unwrap() {
            if row["action"].as_i64() != Some(1) || row["norm"].as_f64().unwrap() < 0.6 {
                continue;
            }
            let vector = |key: &str| {
                let values = row[key].as_array().unwrap();
                std::array::from_fn(|i| values[i].as_f64().unwrap() as f32)
            };
            let selected = select(Inputs {
                norm: row["norm"].as_f64().unwrap() as f32,
                direction: vector("direction"), forward: vector("forward"), right: vector("right"),
                last_action: row["last_action"].as_i64().unwrap() as i32,
                bypass_cooldown: row["bypass_cooldown"].as_i64().unwrap() as i32,
                // Audit preserves already-rounded native subtraction.
                global_time: row["cooldown_age"].as_f64().unwrap() as f32,
                time_offset: 0., last_gate_time: 0.,
                mode: row["mode"].as_i64().unwrap() as i32,
                speed: row["speed"].as_f64().unwrap() as f32,
                configured_action: row["configured_action"].as_i64().unwrap() as i32,
            });
            if slow {
                assert_eq!(selected, None, "Slow ramp rotated before strength gate opened");
                rejected_slow += 1;
            } else {
                assert_eq!(selected, Some(116), "Fast/medium candidate selects observed turn");
                accepted += 1;
            }
        }
    }
    assert!(accepted >= 2 && rejected_slow >= 2);
}
