use crate::{assets::Source, camera::orbit::Orbit, debug::capture::Readiness};
use bevy::{
    image::{ImageAddressMode, ImageSamplerDescriptor},
    prelude::*,
};
use std::{collections::HashSet, path::PathBuf};
pub(crate) fn run() -> bevy::app::AppExit {
    let mut args = std::env::args().skip(1);
    let mut root = None;
    let mut screenshot = None;
    let mut scene_path = PathBuf::from("scene.json");
    let mut localization_path = None;
    let mut text_key = None;
    let mut exit_after_capture = false;
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--scene" => scene_path = args.next().map(PathBuf::from).unwrap_or(scene_path),
            "--assets" => root = args.next().map(PathBuf::from),
            "--screenshot" => screenshot = args.next().map(PathBuf::from),
            "--localization" => localization_path = args.next().map(PathBuf::from),
            "--text-key" => text_key = args.next(),
            "--exit-after-capture" => exit_after_capture = true,
            _ => {
                eprintln!(
                    "Usage: rebge --assets <external-export-directory> [--screenshot <external.png>]"
                );
                std::process::exit(2);
            }
        }
    }
    let root = root.unwrap_or_else(|| {
        eprintln!("Missing --assets. Run export_hangar.py first.");
        std::process::exit(2)
    });
    let root = root.canonicalize().unwrap_or_else(|e| {
        eprintln!("Asset directory: {e}");
        std::process::exit(2)
    });
    let scene = crate::assets::scene::load_scene(&root, &scene_path).unwrap_or_else(|e| {
        eprintln!("{e}");
        std::process::exit(2)
    });
    let localization = crate::assets::localization::load_sample(localization_path, text_key);
    println!(
        "Scene: {} | objects: {} | batches: {} | triangles: {}",
        scene.name,
        scene
            .batches
            .iter()
            .map(|b| &b.object)
            .collect::<HashSet<_>>()
            .len(),
        scene.batches.len(),
        scene
            .batches
            .iter()
            .map(|b| b.vertices.len() / 15)
            .sum::<usize>()
    );
    let camera_target = scene
        .preview_camera
        .as_ref()
        .map(|c| Vec3::from_array(c.target))
        .unwrap_or(Vec3::new(95., 4., -5.));
    let camera_distance = scene
        .preview_camera
        .as_ref()
        .map(|c| c.distance)
        .unwrap_or(15.);
    let window_title = format!("REBGE | {} | diagnostic", scene.name);
    let camera_yaw = scene.preview_camera.as_ref().and_then(|c| c.yaw).unwrap_or(0.8);
    let camera_pitch = scene.preview_camera.as_ref().and_then(|c| c.pitch).unwrap_or(0.25);
    App::new()
        .add_plugins(
            DefaultPlugins
                .set(bevy::render::RenderPlugin {
                    synchronous_pipeline_compilation: true,
                    ..default()
                })
                .set(AssetPlugin {
                    file_path: root.to_string_lossy().into_owned(),
                    ..default()
                })
                .set(ImagePlugin {
                    default_sampler: ImageSamplerDescriptor {
                        address_mode_u: ImageAddressMode::Repeat,
                        address_mode_v: ImageAddressMode::Repeat,
                        ..ImageSamplerDescriptor::linear()
                    },
                })
                .set(WindowPlugin {
                    primary_window: Some(Window {
                        title: window_title,
                        resolution: (1280, 720).into(),
                        ..default()
                    }),
                    ..default()
                }),
        )
        .insert_resource(Source {
            scene,
            root,
            screenshot,
            localization,
            exit_after_capture,
        })
        .insert_resource(Orbit {
            yaw: camera_yaw,
            pitch: camera_pitch,
            distance: camera_distance,
            initial_distance: camera_distance,
            initial_yaw: camera_yaw,
            initial_pitch: camera_pitch,
            target: camera_target,
            input: Vec3::ZERO,
        })
        .insert_resource(Readiness::default())
        .insert_resource(Time::<Fixed>::from_hz(60.))
        .add_systems(FixedUpdate,crate::world::animation::update)
        .insert_resource(ClearColor(Color::srgb(0.07, 0.10, 0.14)))
        .add_systems(
            Startup,
            (
                crate::world::scene::spawn_scene,
                crate::camera::orbit::spawn_camera,
                crate::ui::diagnostics::spawn_diagnostics,
            ),
        )
        .add_systems(
            Update,
            (
                crate::camera::orbit::camera_controls,
                crate::world::animation::controls,
                crate::debug::capture::capture,
            ).chain(),
        )
        .run()
}
