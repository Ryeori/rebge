//! Bevy input, mesh publication, and camera target bridge.
use super::*;

pub(crate) fn update(
    player: Option<ResMut<Player>>,
    source: Res<Source>,
    time: Res<Time<Fixed>>,
    mut query: Query<(&AnimatedBatch, &Mesh3d, &mut Transform)>,
    mut meshes: ResMut<Assets<Mesh>>,
    mut orbit: ResMut<crate::camera::orbit::Orbit>,
    mut movement_trace: Local<MovementTrace>,
) {
    let Some(mut player) = player else { return };
    if player.stopped || player.paused {
        return;
    }
    match player.step(time.delta_secs(), &source) {
        Ok(vertices) => {
            let actor = player.pose.nodes[&player.seed.actor_address].world;
            movement_trace.record(&player, time.delta_secs(), &vertices);
            let position = Vec3::from_array(jade_to_bevy(&std::array::from_fn::<_, 3, _>(|i| {
                actor[12 + i] - player.motion_origin[i]
            }))) + Vec3::from_array(source.scene.actor_spawn.unwrap_or([0.; 3]));
            let transform = if source.scene.root_motion {
                let x = Vec3::from_array(jade_to_bevy(&actor[0..3]));
                let y = Vec3::from_array(jade_to_bevy(&actor[8..11]));
                let z = -Vec3::from_array(jade_to_bevy(&actor[4..7]));
                orbit.target = position + Vec3::Y * 0.8;
                Transform::from_matrix(Mat4::from_cols(
                    x.extend(0.),
                    y.extend(0.),
                    z.extend(0.),
                    position.extend(1.),
                ))
            } else {
                Transform::default()
            };
            for (index, positions) in vertices {
                for (batch, handle, mut entity_transform) in &mut query {
                    if batch.0 == index {
                        if let Some(mut mesh) = meshes.get_mut(&handle.0) {
                            mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, positions.clone());
                            if let Some((_, uvs)) =
                                player.projected_uvs.iter().find(|(i, _)| *i == index)
                            {
                                mesh.insert_attribute(Mesh::ATTRIBUTE_UV_0, uvs.clone());
                            }
                            *entity_transform = transform;
                        }
                    }
                }
            }
        }
        Err(reason) => {
            player.stopped = true;
            error!("Diagnostic animation stopped: {reason}");
        }
    }
}

pub(crate) fn controls(
    player: Option<ResMut<Player>>,
    source: Res<Source>,
    keys: Res<ButtonInput<KeyCode>>,
    gamepads: Query<&Gamepad>,
    orbit: Res<crate::camera::orbit::Orbit>,
) {
    let Some(mut player) = player else { return };
    if keys.just_pressed(KeyCode::KeyR) {
        match load(&source) {
            Ok(Some(restarted)) => *player = restarted,
            Err(e) => error!("Cannot restart diagnostic playback: {e}"),
            _ => {}
        }
    }
    if keys.just_pressed(KeyCode::KeyP) {
        player.paused = !player.paused;
    }
    if player.seed.controls.is_some() {
        let forward =
            i32::from(keys.pressed(KeyCode::KeyW)) - i32::from(keys.pressed(KeyCode::KeyS));
        let right = i32::from(keys.pressed(KeyCode::KeyD)) - i32::from(keys.pressed(KeyCode::KeyA));
        let (s, c) = orbit.yaw.sin_cos();
        // Camera-relative keyboard mapping is a preview policy.
        let keyboard = Vec2::new(right as f32, forward as f32);
        // Preview input policy: keyboard takes priority; retain stick magnitude
        // for the native scalar selector. Dead zone is provisional.
        let stick = gamepads
            .iter()
            .map(|pad| crate::input::stick::movement_stick(pad.left_stick()))
            .find(|s| *s != Vec2::ZERO)
            .unwrap_or(Vec2::ZERO)
            .clamp_length_max(1.);
        let input = if keyboard != Vec2::ZERO {
            keyboard.clamp_length_max(1.)
        } else {
            stick
        };
        player.input_strength = input.length();
        player.control_direction =
            (Vec3::new(-c, -s, 0.) * input.y + Vec3::new(-s, c, 0.) * input.x).normalize_or_zero();
        player.run_requested = keys.pressed(KeyCode::ShiftLeft)
            || keys.pressed(KeyCode::ShiftRight)
            || gamepads.iter().any(|pad| {
                pad.pressed(GamepadButton::RightTrigger2)
                    || pad.get(GamepadButton::RightTrigger2).unwrap_or(0.) > 0.25
            });
        if let Err(reason) = player.request_move(input != Vec2::ZERO) {
            player.stopped = true;
            error!("Diagnostic input failed: {reason}");
        }
    }
}

