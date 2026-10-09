use super::*;
#[test]
#[ignore = "Private independent held-R2 start and R2 release recordings"]
fn recorded_ordinary_run_mode_tables() {
    let mode1 = [0, 1, 1, 1, 1, 1, 1, 1, 4, 3, 116, 123];
    for trace in ["014918", "015026"] {
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join(format!(
            "../reports/jade/stage43-tracking-sequence-20261010-{trace}.json"));
        let raw: serde_json::Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
        let mut mode2_count = 0;
        let mut high_walking_count = 0;
        let mut chain = Vec::new();
        for sample in raw["samples"].as_array().unwrap() {
            let s = &sample["selector_inputs"];
            if s["unchanged"] != true || sample["action_selection_unchanged"] != true { continue; }
            let prefix = s["prefix_hex"].as_str().unwrap();
            let bytes: Vec<u8> = (0x34*2..0x38*2).step_by(2)
                .map(|i| u8::from_str_radix(&prefix[i..i+2],16).unwrap()).collect();
            let mode = i32::from_le_bytes(bytes.try_into().unwrap());
            if !(1..=2).contains(&mode) { continue; }
            let observed: [i32;12] = serde_json::from_value(s["actions_04_30"].clone()).unwrap();
            assert_eq!(ordinary_action_table(mode1, mode == 2), observed,
                "trace {trace}, sample {}", sample["index"]);
            let action = sample["current_action_index_a8"].as_i64().unwrap();
            if chain.last() != Some(&action) { chain.push(action); }
            if mode == 2 {
                mode2_count += 1;
                let value = s["selection_value_48"].as_f64().unwrap() as f32;
                if value >= 0.35 {
                    let selected = moving_action(value, &observed, false, false, false).unwrap().unwrap();
                    assert_ne!(selected, 4);
                    if selected == 3 { high_walking_count += 1; }
                }
            }
        }
        assert!(mode2_count > 10 && high_walking_count > 0);
        assert!(chain.starts_with(&[123, 1, 3, 2]), "trace {trace}: {chain:?}");
    }
}
#[test]
#[ignore = "Private short W pulse recording"]
fn recorded_release_blend_gate() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-tracking-sequence-20261009-152531.json");
    let raw: serde_json::Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    for (before, after, expected_active, expected_action) in
        [(36, 37, true, 1), (42, 43, false, 0)]
    {
        let a = &raw["samples"][before];
        let b = &raw["samples"][after];
        assert_eq!(a["selector_inputs"]["unchanged"], true);
        assert_eq!(b["selector_inputs"]["unchanged"], true);
        assert_eq!(a["action_selection_unchanged"], true);
        assert_eq!(b["action_selection_unchanged"], true);
        assert_eq!(a["selector_inputs"]["selection_value_48"], 0.);
        assert_eq!(a["selector_inputs"]["primary_disabled"], false);
        assert_eq!(
            a["selector_inputs"]["exception_flags"].as_u64().unwrap() & 0x80,
            0
        );
        let h = a["transition_header_hex"].as_str().unwrap();
        let byte = |i: usize| u8::from_str_radix(&h[i * 2..i * 2 + 2], 16).unwrap();
        let gate = crate::animation::transition::advance_transition(
            true,
            byte(0x59),
            u16::from_le_bytes([byte(0x5a), byte(0x5b)]),
            b["delta_time"].as_f64().unwrap() as f32,
        )
        .unwrap();
        assert_eq!(gate.active, expected_active);
        assert_eq!(b["current_action_index_a8"], expected_action);
    }
    // The new idle blend is active in43; it must not be confused with
    // the outgoing blend that gated the request in42.
}
#[test]
#[ignore = "Private stationary selector capture"]
fn recorded_stationary_requests() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-tracking-sequence-20261009-150304.json");
    let raw: serde_json::Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let mut checked = 0;
    for sample in raw["samples"].as_array().unwrap() {
        let s = &sample["selector_inputs"];
        let x = &sample["stationary_selector_inputs"];
        if s["unchanged"] != true
            || x["unchanged"] != true
            || sample["action_selection_unchanged"] != true
            || s["selection_value_48"].as_f64().unwrap() >= 0.35
        {
            continue;
        }
        let decode = |hex: &serde_json::Value| {
            let hex = hex.as_str().unwrap();
            let bytes: Vec<u8> = (0..8)
                .step_by(2)
                .map(|i| u8::from_str_radix(&hex[i..i + 2], 16).unwrap())
                .collect();
            f32::from_le_bytes(bytes.try_into().unwrap())
        };
        let actions: [i32; 12] = serde_json::from_value(s["actions_04_30"].clone()).unwrap();
        let decision = stationary_action(&StationaryInputs {
            mode: x["mode_34"].as_i64().unwrap() as i32,
            pending: x["pending_44"].as_i64().unwrap() as i32,
            last_action: x["last_action_10c4"].as_i64().unwrap() as i32,
            selected_action: x["selected_action_1124"].as_i64().unwrap() as i32,
            scene_time: decode(&x["globals_hex"]["0x1420a3310"]),
            time_origin: decode(&x["globals_hex"]["0x14210c174"]),
            interaction_time: decode(&x["brain_hex"]["0xdac"]),
            action_time: decode(&x["brain_hex"]["0x7b8"]),
            idle: actions[0],
            waiting: actions[11],
            primary_disabled: s["primary_disabled"].as_bool().unwrap(),
            blend_active: s["blend_active"].as_bool().unwrap(),
            exception: s["exception_flags"].as_u64().unwrap() & 0x80 != 0,
        });
        if let Some(requested) = decision.requested {
            let queued = sample["requested_action_index_aa"].as_i64().unwrap();
            let native = if queued == 65535 {
                sample["current_action_index_a8"].as_i64().unwrap()
            } else {
                queued
            };
            assert_eq!(requested as i64, native, "snapshot {}", sample["index"]);
            checked += 1;
        }
    }
    assert!(checked > 100);
    eprintln!(
        "Stationary compatible requests: {checked}; sequential snapshots, not callback execution proof"
    );
}
#[test]
#[ignore = "Private selector input capture"]
fn recorded_moving_selector_and_norm() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-tracking-sequence-20261009-145240.json");
    let raw: serde_json::Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let samples = raw["samples"].as_array().unwrap();
    let mut checked = 0;
    let mut norm_checked = 0;
    let mut norm_mismatches = Vec::new();
    for pair in samples.windows(2) {
        let (a, b) = (&pair[0], &pair[1]);
        let (x, y) = (&a["selector_inputs"], &b["selector_inputs"]);
        if x["unchanged"] != true || y["unchanged"] != true {
            continue;
        }
        let before = x["selection_value_48"].as_f64().unwrap() as f32;
        let value = y["selection_value_48"].as_f64().unwrap() as f32;
        if before < 0.35 || value < 0.35 {
            continue;
        }
        let delta = b["delta_time"].as_f64().unwrap() as f32;
        // Forward held-W interval observed in external input log.
        if before >= 0.35 && value >= before {
            let actual = joy_norm(before, 1., delta, true, false).unwrap();
            if actual == value {
                norm_checked += 1;
            } else {
                norm_mismatches.push(b["index"].as_u64().unwrap());
            }
        }
        let header = a["transition_header_hex"].as_str().unwrap();
        let byte = |i: usize| u8::from_str_radix(&header[i * 2..i * 2 + 2], 16).unwrap();
        let elapsed = u16::from_le_bytes([byte(0x5a), byte(0x5b)]);
        let active = crate::animation::transition::advance_transition(
            x["blend_active"].as_bool().unwrap(),
            byte(0x59),
            elapsed,
            delta,
        )
        .unwrap()
        .active;
        let actions: [i32; 12] = serde_json::from_value(y["actions_04_30"].clone()).unwrap();
        let predicted = moving_action(
            before,
            &actions,
            active,
            x["primary_disabled"].as_bool().unwrap(),
            y["exception_flags"].as_u64().unwrap() & 0x80 != 0,
        )
        .unwrap();
        let expected = b["current_action_index_a8"].as_i64().unwrap() as i32;
        let predicted =
            predicted.unwrap_or(a["current_action_index_a8"].as_i64().unwrap() as i32);
        assert_eq!(predicted, expected, "sample {}", b["index"]);
        checked += 1;
    }
    assert!(checked > 50 && norm_checked > 50);
    eprintln!(
        "Selector: {checked}; scalar exact candidates: {norm_checked}; scalar mismatches: {norm_mismatches:?}"
    );
}
