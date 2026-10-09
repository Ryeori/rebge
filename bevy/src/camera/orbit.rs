use bevy::input::mouse::{AccumulatedMouseMotion, AccumulatedMouseScroll, MouseScrollUnit};
use bevy::prelude::*;
#[derive(Resource)]
pub(crate) struct Orbit {
    pub(crate) yaw: f32,
    pub(crate) pitch: f32,
    pub(crate) distance: f32,
    pub(crate) initial_distance: f32,
    pub(crate) initial_yaw: f32,
    pub(crate) initial_pitch: f32,
    pub(crate) target: Vec3,
    pub(crate) input: Vec3,
}
pub(crate) fn camera_controls(
    keys: Res<ButtonInput<KeyCode>>,
    buttons: Res<ButtonInput<MouseButton>>,
    motion: Res<AccumulatedMouseMotion>,
    scroll: Res<AccumulatedMouseScroll>,
    time: Res<Time>,
    gamepads: Query<&Gamepad>,
    mut orbit: ResMut<Orbit>,
    mut cameras: Query<&mut Transform, With<Camera3d>>,
) {
    let step = time.delta_secs();
    let axis = |positive, negative| {
        i32::from(keys.pressed(positive)) as f32 - i32::from(keys.pressed(negative)) as f32
    };
    let requested = Vec3::new(
        axis(KeyCode::ArrowLeft, KeyCode::ArrowRight),
        axis(KeyCode::ArrowUp, KeyCode::ArrowDown),
        axis(KeyCode::Minus, KeyCode::Equal),
    );
    orbit.input = crate::input::blend::blend_direction(orbit.input, requested, step);
    orbit.yaw += orbit.input.x * step;
    orbit.pitch += orbit.input.y * step;
    orbit.distance *= (orbit.input.z * step).exp();
    // Preview camera sensitivity/dead zone; native camera not reconstructed.
    let stick = gamepads
        .iter()
        .map(Gamepad::right_stick)
        .find(|s| s.length() > 0.15)
        .unwrap_or(Vec2::ZERO)
        .clamp_length_max(1.);
    orbit.yaw -= stick.x * 2.0 * step;
    orbit.pitch += stick.y * 1.5 * step;
    // Preview orbit policy. Mouse deltas already cover this frame: no dt factor.
    if buttons.pressed(MouseButton::Right) {
        orbit.yaw -= motion.delta.x * 0.004;
        orbit.pitch += motion.delta.y * 0.004;
    }
    let wheel_scale = match scroll.unit {
        MouseScrollUnit::Line => 0.12,
        MouseScrollUnit::Pixel => 0.001,
    };
    orbit.distance *= (-scroll.delta.y * wheel_scale).exp();
    if keys.just_pressed(KeyCode::Home) {
        orbit.yaw = orbit.initial_yaw;
        orbit.pitch = orbit.initial_pitch;
        orbit.distance = orbit.initial_distance;
        orbit.input = Vec3::ZERO;
    }
    orbit.pitch = orbit.pitch.clamp(-1.5, 1.5);
    orbit.distance = orbit.distance.clamp(0.5, 1000.);
    let eye = orbit.target
        + Vec3::new(
            orbit.distance * orbit.pitch.cos() * orbit.yaw.cos(),
            orbit.distance * orbit.pitch.sin(),
            -orbit.distance * orbit.pitch.cos() * orbit.yaw.sin(),
        );
    for mut transform in &mut cameras {
        *transform = Transform::from_translation(eye).looking_at(orbit.target, Vec3::Y);
    }
}

pub(crate) fn spawn_camera(mut commands: Commands) {
    commands.spawn((
        Camera3d::default(),
        bevy::core_pipeline::tonemapping::Tonemapping::None,
        Transform::default(),
    ));
}
