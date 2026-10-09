use super::*;
#[test]
#[ignore = "Private native direction filter record"]
fn recorded_direction_updates() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-speed-order-20261009-161128.json");
    let raw: serde_json::Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let decode = |value: &serde_json::Value| {
        let h = value.as_str().unwrap();
        (0..h.len())
            .step_by(2)
            .map(|i| u8::from_str_radix(&h[i..i + 2], 16).unwrap())
            .collect::<Vec<_>>()
    };
    let vector = |value: &serde_json::Value| {
        let bytes = decode(value);
        Vec3::from_array(std::array::from_fn(|i| {
            f32::from_le_bytes(bytes[i * 4..i * 4 + 4].try_into().unwrap())
        }))
    };
    for (before, after) in [(113, 114), (134, 135), (632, 633)] {
        let a = &raw["rows"][before];
        let b = &raw["rows"][after];
        assert_eq!(a["unchanged"], true);
        assert_eq!(b["unchanged"], true);
        assert_eq!(a["raw_input_hex"], b["raw_input_hex"]);
        assert_eq!(a["delta_hex"], b["delta_hex"]);
        let delta = f32::from_le_bytes(decode(&b["delta_hex"]).try_into().unwrap());
        let observed = vector(&b["filtered_hex"]);
        let actual = blend_direction(
            vector(&a["filtered_hex"]),
            vector(&b["raw_input_hex"]),
            delta,
        );
        assert_eq!(
            actual.to_array().map(f32::to_bits),
            observed.to_array().map(f32::to_bits)
        );
    }
}
#[test]
fn recovered_blend_step_and_release() {
    let first = blend_direction(Vec3::ZERO, Vec3::X, 1.0 / 60.0);
    assert!((first.x - 0.2).abs() < 1e-6);
    let second = blend_direction(first, Vec3::X, 1.0 / 60.0);
    assert!((second.x - 0.36).abs() < 1e-6);
    let released = blend_direction(second, Vec3::ZERO, 1.0 / 60.0);
    assert!((released.x - 0.288).abs() < 1e-6);
}
#[test]
fn clamped_delta_does_not_extrapolate() {
    assert_eq!(blend_direction(Vec3::X, Vec3::Y, -1.0), Vec3::X);
    assert_eq!(blend_direction(Vec3::X, Vec3::Y, 1.0), Vec3::Y);
}
