use super::*;

// Structural checks only; these are not independently measured native parity.
#[test]
fn structural_zero_delta_retains_response() {
    let result = step(Inputs {
        runtime_velocity: [0., 0.], response: 1.25, delta: 0.,
    });
    assert_eq!(result.response, 1.25);
    assert_eq!(result.factor, 0.);
}

#[test]
fn structural_response_and_factor_are_bounded() {
    let result = step(Inputs {
        runtime_velocity: [100., 100.], response: 0., delta: 1.,
    });
    assert_eq!(result.response, 3.);
    assert_eq!(result.factor, 1.);
    let ordinary = step(Inputs {
        runtime_velocity: [0., 0.], response: 1., delta: 1. / 60.,
    });
    assert!(ordinary.response > 1. && ordinary.response < 3.);
    assert!(ordinary.factor > 0. && ordinary.factor < 1.);
}

#[test]
fn structural_mode1_zero_delta_retains_response() {
    let result = mode1_yaw(Mode1Inputs {
        signed_angle: 1., norm: 1., previous_response1198: 0.5, delta: 0.,
    });
    assert_eq!(result.updated_response, 0.5);
    assert_eq!(result.yaw, 0.);
}

#[test]
fn structural_mode1_sign_and_zero_norm() {
    let inputs = Mode1Inputs {
        signed_angle: 1., norm: 1., previous_response1198: 1., delta: 1. / 60.,
    };
    let positive = mode1_yaw(inputs);
    let negative = mode1_yaw(Mode1Inputs { signed_angle: -1., ..inputs });
    assert_eq!(positive.updated_response, 1.);
    assert!(positive.yaw > 0. && positive.yaw < 1.);
    assert_eq!(positive.yaw, -negative.yaw);
    assert_eq!(mode1_yaw(Mode1Inputs { norm: 0., ..inputs }).yaw, 0.);
}
