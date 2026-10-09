use super::*;
use serde::Deserialize;

#[test]
fn matrix_extraction_covers_half_turn_axes() {
    for q in [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ] {
        let matrix = quaternion_matrix(q);
        let recovered = quaternion_matrix(matrix_quaternion(matrix).unwrap());
        assert_eq!(matrix, recovered);
    }
}

#[test]
fn opposite_quaternion_signs_keep_first_rotation() {
    let first = [0.0, 0.0, 0.0, 1.0];
    assert_eq!(
        blend_rotation(first, [0.0, 0.0, 0.0, -1.0], 0.3).unwrap(),
        first
    );
}

#[derive(Deserialize)]
struct NativePose {
    slot: u16,
    incoming: [f32; 16],
    saved_primary: [f32; 16],
    weight: f32,
    observed: [f32; 16],
}

#[test]
#[ignore = "requires private original-game pose fixture under reports/jade"]
fn recorded_local_pose_transitions() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-bevy-local-blend-native.json");
    let text =
        std::fs::read_to_string(path).expect("Generate private native pose fixture first");
    let cases: Vec<NativePose> = serde_json::from_str(&text).unwrap();
    assert_eq!(cases.len(), 684);
    let mut rotation_max = 0.0_f32;
    let mut position_max = 0.0_f32;
    for case in cases {
        let result =
            blend_local_no_scale(case.incoming, 6, case.saved_primary, 6, case.weight).unwrap();
        for index in [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14] {
            // Root translation must undergo its separate reference stage.
            if case.slot == 0 && index >= 12 {
                continue;
            }
            let error = (result[index] - case.observed[index]).abs();
            if index < 12 {
                rotation_max = rotation_max.max(error);
            } else {
                position_max = position_max.max(error);
            }
            assert!(
                (result[index] - case.observed[index]).abs() <= 1e-5,
                "Native local component {index}: {} != {}",
                result[index],
                case.observed[index]
            );
        }
    }
    println!(
        "Native local blend:684 rotations; max={rotation_max}; non-root position max={position_max}"
    );
}
