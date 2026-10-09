use crate::assets::Source;
use bevy::prelude::*;
use std::path::PathBuf;
pub(crate) fn spawn_diagnostics(
    mut commands: Commands,
    source: Res<Source>,
    mut fonts: ResMut<Assets<Font>>,
) {
    let font = std::env::var_os("WINDIR")
        .and_then(|p| std::fs::read(PathBuf::from(p).join("Fonts/arial.ttf")).ok())
        .map(|bytes| fonts.add(Font::from_bytes(bytes)))
        .unwrap_or_else(|| {
            warn!("System Arial unavailable; default font may lack Cyrillic");
            Handle::default()
        });
    let mode = if source.scene.locomotion_controls {
        "WASD / left stick: move  |  Shift / R2: run  |  approximate selection/steering, no collision  |  R: reset  |  P: pause"
    } else if source.scene.root_motion {
        "Source root motion  |  no collision  |  R: replay  |  P: pause"
    } else if source.scene.animation.is_some() {
        "Source clip playback  |  fixed root  |  R: replay  |  P: pause"
    } else {
        "Static reconstruction  |  simplified materials  |  no gameplay"
    };
    commands.spawn((
        Text::new(format!(
            "Jade  |  {}\nRight stick / right mouse drag / arrows: orbit | Wheel / +/-: zoom | Home: reset | Space: screenshot\n{}{}",
            source.scene.name, mode, source.localization
        )),
        TextFont {
            font: bevy::text::FontSource::Handle(font),
            font_size: bevy::text::FontSize::Px(18.),
            ..default()
        },
        Node {
            position_type: PositionType::Absolute,
            top: px(12),
            left: px(12),
            padding: UiRect::all(px(8)),
            ..default()
        },
        BackgroundColor(Color::srgba(0.03, 0.04, 0.05, 0.85)),
    ));
}
