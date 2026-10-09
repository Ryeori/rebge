use super::*;

#[test]
fn independent_native_probe_bounds() {
    // Qualified WinMM delivered values from stick-threshold-audit-20261009.
    for strength in [0.19049072, 0.24606323, 0.29367065, 0.34127808] {
        assert_eq!(movement_stick(Vec2::new(0., strength)), Vec2::ZERO);
    }
    // Standing-ramp native input norm 0x3eb6b400 was accepted as action 1.
    let accepted = f32::from_bits(0x3eb6b400);
    assert_eq!(movement_stick(Vec2::new(accepted, 0.)).x, accepted);
    assert_eq!(movement_stick(Vec2::new(0., 0.5000305)).y, 0.5000305);
}

#[test]
fn native_listing_component_boundary_and_diagonal() {
    // Instruction-level boundary; independent gameplay probes cover axes.
    assert_eq!(movement_stick(Vec2::splat(0.30)), Vec2::ZERO);
    assert_eq!(movement_stick(Vec2::new(-MOVEMENT_DEADZONE, MOVEMENT_DEADZONE)), Vec2::ZERO);
    let above = f32::from_bits(0x3eb33334);
    assert_eq!(movement_stick(Vec2::new(-above, 0.)), Vec2::new(-above, 0.));
    assert_eq!(movement_stick(Vec2::new(above, 0.30)), Vec2::new(above, 0.30));
    assert_eq!(movement_stick(Vec2::new(FULL_STICK_THRESHOLD, 0.)).x, FULL_STICK_THRESHOLD);
    assert_eq!(movement_stick(Vec2::new(0.95, 0.)).x, 1.);
}
