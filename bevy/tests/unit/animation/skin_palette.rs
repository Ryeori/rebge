use super::*;
use serde::Deserialize;
#[derive(Deserialize)]
struct Actor {
    world_matrix: Vec<f32>,
}
#[derive(Deserialize)]
struct Object {
    slot: usize,
    matrix: Option<[f32; 16]>,
    matrix_flags: Option<u32>,
}
#[derive(Deserialize)]
struct Matrix {
    slot: usize,
    matrix: [f32; 16],
    flags: u32,
}
#[derive(Deserialize)]
struct Palette {
    count: usize,
    matrices: Vec<Matrix>,
}
#[derive(Deserialize)]
struct Snapshot {
    actor: Actor,
    objects: Vec<Object>,
    palette: Palette,
}

#[test]
#[ignore = "Requires private post-procedural native palette snapshot"]
fn recorded_actor_relative_palette() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage4-sally-runtime-20261008-172956.json");
    let record: Snapshot = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let actor: [f32; 16] = record.actor.world_matrix[..16].try_into().unwrap();
    let actor_flags = record.actor.world_matrix[16] as u32;
    assert_eq!(record.palette.count, 47);
    assert_eq!(record.palette.matrices.len(), 47);
    for expected in record.palette.matrices {
        let bone = record
            .objects
            .iter()
            .find(|o| o.slot == expected.slot)
            .unwrap();
        let (actual, flags) = palette_matrix(
            actor,
            actor_flags,
            bone.matrix.unwrap(),
            bone.matrix_flags.unwrap(),
        )
        .unwrap();
        for i in [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14] {
            assert!(
                (actual[i] - expected.matrix[i]).abs() <= 1e-5,
                "palette slot {} component {}",
                expected.slot,
                i
            );
        }
        assert_eq!(flags & 6, expected.flags & 6);
    }
}
