use super::*;
#[test]
#[ignore = "Private narrow native angular observation"]
fn recorded_angular_speed_with_prior_world() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-speed-order-20261009-160521.json");
    let raw: serde_json::Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let decode = |value: &serde_json::Value| {
        let h = value.as_str().unwrap();
        (0..h.len())
            .step_by(2)
            .map(|i| u8::from_str_radix(&h[i..i + 2], 16).unwrap())
            .collect::<Vec<_>>()
    };
    for index in [55, 56, 57] {
        let row = &raw["rows"][index];
        assert_eq!(row["unchanged"], true);
        let state = decode(&row["state_hex"]);
        let word = |offset| i32::from_le_bytes(state[offset..offset + 4].try_into().unwrap());
        assert_eq!(word(0x20), 1);
        // The snapshot spans an action change. Stored speed60 is observed,
        // but the pre-writer refresh source is not captured atomically.
        assert_eq!(word(0x34), 60);
        // Row54 precedes the speed43 publication and actor rotation in55.
        // Three rows55..57 observe one event, not three independent turns.
        let preceding = &raw["rows"][54];
        assert_eq!(preceding["unchanged"], true);
        assert_eq!(preceding["direction_hex"], row["direction_hex"]);
        assert_eq!(preceding["norm_hex"], row["norm_hex"]);
        let world = decode(&preceding["world_hex"]);
        let direction = decode(&row["direction_hex"]);
        assert_eq!(
            u32::from_le_bytes(decode(&row["flags_hex"]).try_into().unwrap()) & 0x400000,
            0
        );
        let output = evaluate(&Inputs {
            gate: i32::from_le_bytes(decode(&row["gate_hex"]).try_into().unwrap()),
            mode: word(0x20),
            stored_speed: word(0x34),
            input_norm: f32::from_le_bytes(decode(&row["norm_hex"]).try_into().unwrap()),
            forward: std::array::from_fn(|i| {
                -f32::from_le_bytes(world[(i + 4) * 4..(i + 5) * 4].try_into().unwrap())
            }),
            direction: std::array::from_fn(|i| {
                f32::from_le_bytes(direction[i * 4..i * 4 + 4].try_into().unwrap())
            }),
        })
        .unwrap();
        assert!(output.angle.is_some());
        assert_eq!(output.mode, 1);
        assert_eq!(
            output.speed,
            decode(&row["header_hex"])[2],
            "native row{index}:angle{:?}",
            output.angle
        );
    }
}
#[test]
#[ignore = "Private native speed writer inputs"]
fn recorded_speed_bytes() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-tracking-sequence-20261009-155405.json");
    let raw: serde_json::Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let mut exact = 0;
    let mut angular = 0;
    let mut mismatches = Vec::new();
    for sample in raw["samples"].as_array().unwrap() {
        let s = &sample["speed_writer_inputs"];
        if s["unchanged"] != true || sample["primary_header_unchanged"] != true {
            continue;
        }
        let decode = |value: &serde_json::Value| {
            let h = value.as_str().unwrap();
            (0..h.len())
                .step_by(2)
                .map(|i| u8::from_str_radix(&h[i..i + 2], 16).unwrap())
                .collect::<Vec<_>>()
        };
        let state = decode(&s["state_10c4_hex"]);
        let word = |i| i32::from_le_bytes(state[i..i + 4].try_into().unwrap());
        // Refresh branch consumes pre-writer header speed, not a late snapshot.
        if word(0x2c) != word(0) || word(0x30) != word(0x28) {
            continue;
        }
        let actor_flags = u32::from_str_radix(
            sample["actor"]["flags"]
                .as_str()
                .unwrap()
                .trim_start_matches("0x"),
            16,
        )
        .unwrap();
        if actor_flags & 0x400000 != 0 {
            continue;
        }
        let direction = decode(&s["direction_hex"]);
        let input = decode(&s["input_norm_hex"]);
        let forward = std::array::from_fn(|i| {
            -(sample["actor"]["world_matrix"][i + 4].as_f64().unwrap() as f32)
        });
        let output = evaluate(&Inputs {
            gate: s["gate_1dc"].as_i64().unwrap() as i32,
            mode: word(0x20),
            stored_speed: word(0x34),
            input_norm: f32::from_le_bytes(input.try_into().unwrap()),
            forward,
            direction: std::array::from_fn(|i| {
                f32::from_le_bytes(direction[i * 4..i * 4 + 4].try_into().unwrap())
            }),
        })
        .unwrap();
        angular += output.angle.is_some() as usize;
        let expected = decode(&sample["primary_header_hex"])[2];
        if output.speed == expected {
            exact += 1;
        } else {
            mismatches.push(sample["index"].as_u64().unwrap());
        }
    }
    assert_eq!(exact, 217);
    assert_eq!(angular, 0, "This fixture does not validate angular inputs");
    // Native snapshots cross callback/clip replacement boundaries here.
    // Keep those discrepancies explicit rather than accepting a match rate.
    assert_eq!(mismatches, vec![32, 45, 57, 121]);
    for index in &mismatches {
        let sample = &raw["samples"][*index as usize];
        let header = sample["primary_header_hex"].as_str().unwrap();
        let observed = u8::from_str_radix(&header[4..6], 16).unwrap();
        assert_eq!(observed, source_speed(64));
        assert_ne!(
            sample["current_action_index_a8"],
            raw["samples"][*index as usize - 1]["current_action_index_a8"]
        );
    }
    eprintln!(
        "Speed exact snapshots:{exact}, angular:{angular}, mismatches:{mismatches:?}; sequential capture, not callback proof"
    );
}
