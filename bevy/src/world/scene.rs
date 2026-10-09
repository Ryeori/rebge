use crate::{
    assets::{Source, scene::jade_to_bevy},
    debug::capture::Readiness,
};
use bevy::{asset::RenderAssetUsages, prelude::*, render::render_resource::PrimitiveTopology};
pub(crate) fn spawn_scene(
    mut commands: Commands,
    source: Res<Source>,
    server: Res<AssetServer>,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    mut ready: ResMut<Readiness>,
) {
    match super::animation::load(&source) {
        Ok(Some(player)) => {
            commands.insert_resource(player);
        }
        Ok(None) => {}
        Err(reason) => {
            error!("Cannot load diagnostic animation: {reason}");
            return;
        }
    }
    for (index, b) in source.scene.batches.iter().enumerate() {
        let positions: Vec<[f32; 3]> = b.vertices.chunks_exact(5).map(jade_to_bevy).collect();
        let uv: Vec<[f32; 2]> = b.vertices.chunks_exact(5).map(|v| [v[3], v[4]]).collect();
        let normals = vec![[0., 1., 0.]; positions.len()]; // Unlit preview; source normal interpretation remains pending.
        let mesh = Mesh::new(
            PrimitiveTopology::TriangleList,
            RenderAssetUsages::MAIN_WORLD | RenderAssetUsages::RENDER_WORLD,
        )
        .with_inserted_attribute(Mesh::ATTRIBUTE_POSITION, positions)
        .with_inserted_attribute(Mesh::ATTRIBUTE_NORMAL, normals)
        .with_inserted_attribute(Mesh::ATTRIBUTE_UV_0, uv);
        let texture = b.texture.as_ref().filter(|_| !b.preview_water).map(|t| {
            let h = server.load::<Image>(t.clone());
            ready.images.push(h.clone());
            h
        });
        let material = StandardMaterial {
            base_color: if b.preview_water {
                Color::srgba(0.035, 0.22, 0.27, 0.72)
            } else if texture.is_some() {
                Color::WHITE
            } else {
                Color::srgb(0.56, 0.66, 0.72)
            },
            base_color_texture: texture,
            unlit: true,
            cull_mode: None,
            alpha_mode: if b.preview_water {
                AlphaMode::Blend
            } else {
                AlphaMode::Mask(0.2)
            },
            ..default()
        };
        let mut entity = commands.spawn((
            Name::new(format!("{}:{}", b.object, b.mesh)),
            Mesh3d(meshes.add(mesh)),
            MeshMaterial3d(materials.add(material)),
            Transform::default(),
            Visibility::Visible,
        ));
        if b.deformation.is_some() {
            entity.insert(super::animation::AnimatedBatch(index));
        }
    }
    info!("External asset root: {}", source.root.display());
}
