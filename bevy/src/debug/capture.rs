use crate::assets::Source;
use bevy::{
    prelude::*,
    render::view::screenshot::{Screenshot, save_to_disk},
};
#[derive(Resource, Default)]
pub(crate) struct Readiness {
    pub(crate) images: Vec<Handle<Image>>,
    pub(crate) frames: u32,
    pub(crate) captured: bool,
}

pub(crate) fn capture(
    mut commands: Commands,
    source: Res<Source>,
    images: Res<Assets<Image>>,
    keys: Res<ButtonInput<KeyCode>>,
    mut ready: ResMut<Readiness>,
    time: Res<Time>,
    mut exit: MessageWriter<bevy::app::AppExit>,
) {
    if ready.images.iter().all(|h| images.contains(h)) {
        ready.frames += 1;
    }
    if keys.just_pressed(KeyCode::Space)
        || (source.screenshot.is_some() && ready.frames > 120 && !ready.captured)
    {
        if let Some(path) = &source.screenshot {
            commands
                .spawn(Screenshot::primary_window())
                .observe(save_to_disk(path.clone()));
            ready.captured = true;
        }
    }
    if source.exit_after_capture
        && ready.captured
        && ready.frames > 180
        && source.screenshot.as_ref().is_some_and(|p| p.is_file())
    {
        info!("Capture completed; exiting validation run");
        exit.write(bevy::app::AppExit::Success);
    } else if source.exit_after_capture && time.elapsed_secs() > 120. {
        error!("Timed out waiting for assets or screenshot");
        exit.write(bevy::app::AppExit::error());
    }
}
