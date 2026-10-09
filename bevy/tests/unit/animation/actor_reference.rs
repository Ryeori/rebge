use super::*;
use serde::Deserialize;
#[derive(Deserialize)]
struct Case {
    rotation: [f32; 4],
    observed_matrix: [f32; 16],
    position: [f32; 3],
    reference: [f32; 16],
    reference_flags: u32,
    actor: [f32; 16],
    actor_flags: u32,
    height: f32,
    add_height: bool,
    observed: [f32; 3],
}
#[derive(Deserialize)]
struct Fixture {
    cases: Vec<Case>,
}
#[test]
fn refresh_rotated_actor_and_height_branch() {
    let mut actor = IDENTITY;
    actor[0..3].copy_from_slice(&[0., 1., 0.]);
    actor[4..7].copy_from_slice(&[-1., 0., 0.]);
    actor[12..15].copy_from_slice(&[10., 20., 30.]);
    let mut root = IDENTITY;
    root[12..15].copy_from_slice(&[2., 3., 4.]);
    let (reference, flags) = refresh_reference(root, 2, actor, 6).unwrap();
    assert_eq!(&reference[12..15], &[13., 18., 26.]);
    assert_eq!(
        actor_reference_position([2., 3., 4.], reference, flags, actor, 6, 0.5, true).unwrap(),
        [0., 0., 0.5]
    );
    assert!(actor_reference_position([0.; 3], reference, 8, actor, 6, 0., false).is_err());
}
#[test]
#[ignore = "Requires private native root reference fixture"]
fn stationary_native_root_translation() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-bevy-actor-reference-native.json");
    let fixture: Fixture = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    assert_eq!(fixture.cases.len(), 32);
    for case in fixture.cases {
        let actual = actor_reference_position(
            case.position,
            case.reference,
            case.reference_flags,
            case.actor,
            case.actor_flags,
            case.height,
            case.add_height,
        )
        .unwrap();
        assert_eq!(actual, case.observed);
        let (relative, flags) = actor_relative_reference(
            case.reference,
            case.reference_flags,
            case.actor,
            case.actor_flags,
        )
        .unwrap();
        let local = super::super::pose_blend::quaternion_matrix(case.rotation);
        let (basis, _) =
            compose_reference_basis(IDENTITY, 0, local, 4, relative, flags).unwrap();
        for i in [0, 1, 2, 4, 5, 6, 8, 9, 10] {
            assert!((basis[i] - case.observed_matrix[i]).abs() <= 1e-5);
        }
    }
}

#[test]
#[ignore = "Requires private moving primary/transition root fixture"]
fn recorded_moving_and_transition_root_bases() {
    use super::super::pose_blend::{blend_rotation, matrix_quaternion, quaternion_matrix};
    #[derive(Deserialize)]
    struct Operand {
        rotation: [f32; 4],
        reference: [f32; 16],
        reference_flags: u32,
        actor: [f32; 16],
        actor_flags: u32,
    }
    #[derive(Deserialize)]
    struct RootCase {
        sample: usize,
        active_slots: u8,
        operands: Vec<Operand>,
        weight: Option<f32>,
        observed: [f32; 16],
    }
    #[derive(Deserialize)]
    struct RootFixture {
        cases: Vec<RootCase>,
    }
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-tracking-sequence-20261009-023957-root-rotation.json");
    let fixture: RootFixture = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    assert_eq!(fixture.cases.len(), 186);
    let mut counts = [0; 2];
    let mut maximum = 0.0_f32;
    for case in fixture.cases {
        let bases: Vec<_> = case
            .operands
            .into_iter()
            .map(|operand| {
                let (relative, flags) = actor_relative_reference(
                    operand.reference,
                    operand.reference_flags,
                    operand.actor,
                    operand.actor_flags,
                )
                .unwrap();
                compose_reference_basis(
                    IDENTITY,
                    0,
                    quaternion_matrix(operand.rotation),
                    4,
                    relative,
                    flags,
                )
                .unwrap()
                .0
            })
            .collect();
        let expected = match case.active_slots {
            1 => {
                counts[0] += 1;
                assert_eq!(bases.len(), 1);
                bases[0]
            }
            3 => {
                counts[1] += 1;
                assert_eq!(bases.len(), 2);
                quaternion_matrix(
                    blend_rotation(
                        matrix_quaternion(bases[1]).unwrap(),
                        matrix_quaternion(bases[0]).unwrap(),
                        case.weight.unwrap(),
                    )
                    .unwrap(),
                )
            }
            _ => panic!("Unsupported active slots"),
        };
        for i in [0, 1, 2, 4, 5, 6, 8, 9, 10] {
            let error = (expected[i] - case.observed[i]).abs();
            maximum = maximum.max(error);
            assert!(error <= 1e-5, "sample {} element {i}: {error}", case.sample);
        }
    }
    assert_eq!(counts, [129, 57]);
    eprintln!("root bases 129 primary / 57 transition; max error {maximum}");
}

#[test]
#[ignore = "Requires private sequential temporary-pointer diagnostic; not callback input proof"]
fn recorded_temporary_matrix_refresh_relation() {
    #[derive(Deserialize)]
    struct Case {
        row: usize,
        root: [f32; 16],
        root_flags: u32,
        saved_actor: [f32; 16],
        saved_actor_flags: u32,
        observed_reference: [f32; 16],
        observed_flags: u32,
        accepted_callback_fixture: bool,
        timing_reasons: Vec<String>,
    }
    #[derive(Deserialize)]
    struct Fixture {
        cases: Vec<Case>,
    }
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-reference-order-20261009-032721-windows.json");
    let fixture: Fixture = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    assert_eq!(fixture.cases.len(), 6);
    for case in fixture.cases {
        // Preserve the distinction between a measured numerical relationship
        // and an accepted recording of callback-time inputs.
        assert!(!case.accepted_callback_fixture);
        assert!(!case.timing_reasons.is_empty());
        let (actual, flags) = refresh_reference(
            case.root,
            case.root_flags,
            case.saved_actor,
            case.saved_actor_flags,
        )
        .unwrap();
        assert_eq!(flags, case.observed_flags);
        for i in 0..16 {
            assert_eq!(
                actual[i].to_bits(),
                case.observed_reference[i].to_bits(),
                "sequential diagnostic row {} element {i}",
                case.row
            );
        }
    }
}

#[test]
fn reference_identity_flags_override_raw_basis_and_preserve_translation() {
    let mut raw = IDENTITY;
    raw[0] = 99.;
    let mut reference = IDENTITY;
    reference[0] = 0.;
    reference[1] = 1.;
    reference[4] = -1.;
    reference[5] = 0.;
    let mut prior = IDENTITY;
    prior[12] = 7.;
    let (actual, flags) = compose_reference_basis(prior, 2, raw, 0, reference, 4).unwrap();
    assert_eq!(actual[0], 0.);
    assert_eq!(actual[1], 1.);
    assert_eq!(actual[12], 7.);
    assert_eq!(flags, 6);
}
