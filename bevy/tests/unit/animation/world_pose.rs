use super::*;
use serde::Deserialize;
#[derive(Deserialize)]
struct Input {
    address: u64,
    flags: u32,
    world: [f32; 16],
    world_flags: u32,
    parent: Option<u64>,
    local: Option<[f32; 16]>,
    local_flags: Option<u32>,
}
#[derive(Deserialize)]
struct Expected {
    address: u64,
    slot: usize,
    world: [f32; 16],
}
#[derive(Deserialize)]
struct Case {
    nodes: Vec<Input>,
    expected: Vec<Expected>,
}
#[derive(Deserialize)]
struct Fixture {
    cases: Vec<Case>,
    excluded_slots: Vec<usize>,
}

#[test]
#[ignore = "Requires private observed hierarchy fixture"]
fn recorded_local_to_world_consistency() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-bevy-world-hierarchy-native.json");
    let fixture: Fixture = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    assert_eq!(fixture.excluded_slots, [27, 28]);
    let mut count = 0;
    for case in fixture.cases {
        let nodes: BTreeMap<_, _> = case
            .nodes
            .into_iter()
            .map(|input| {
                (
                    input.address,
                    Node {
                        flags: input.flags,
                        world: input.world,
                        world_flags: input.world_flags,
                        parent: input.parent,
                        local: input
                            .local
                            .map(|m| (m, input.local_flags.expect("Local flags required"))),
                    },
                )
            })
            .collect();
        let worlds = compose_world_pose(&nodes).unwrap();
        for expected in case.expected {
            let (actual, _) = worlds[&expected.address];
            for i in [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14] {
                assert!(
                    (actual[i] - expected.world[i]).abs() <= 1e-5,
                    "slot {} component {}: {} vs {}",
                    expected.slot,
                    i,
                    actual[i],
                    expected.world[i]
                );
            }
            count += 1;
        }
    }
    assert_eq!(count, 360);
}
