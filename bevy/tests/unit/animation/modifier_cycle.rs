use super::super::hierarchy::Node;
use super::*;
use serde::Deserialize;
#[derive(Deserialize)]
struct InputNode {
    address: u64,
    flags: u32,
    world: [f32; 16],
    world_flags: u32,
    parent: Option<u64>,
    local: Option<[f32; 16]>,
    local_flags: Option<u32>,
}
#[derive(Deserialize)]
struct InputRecord {
    bone: usize,
    state_hex: String,
    record_flags: u32,
}
#[derive(Deserialize)]
struct Expected {
    bone: usize,
    world: [f32; 16],
    local: [f32; 16],
    local_flags: u32,
}
#[derive(Deserialize)]
struct Case {
    nodes: Vec<InputNode>,
    bone_addresses: Vec<u64>,
    cycle_records: Vec<InputRecord>,
    cycle_expected: Vec<Expected>,
    requested_bone: usize,
    parent_modifier_bone: usize,
    delta: f32,
    cycle_inputs_available: bool,
}
#[derive(Deserialize)]
struct Fixture {
    cases: Vec<Case>,
}
#[test]
#[ignore = "Private adjacent native records; conditional inputs, not callback chronology"]
fn recorded_parent_child_cycles() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join(
        "../reports/jade/stage43-tracking-sequence-20261008-173533-modifier24-step-native.json",
    );
    let fixture: Fixture = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let mut maximum = 0.0_f32;
    let mut maximum_basis = 0.0_f32;
    let mut maximum_position = 0.0_f32;
    assert_eq!(fixture.cases.len(), 139);
    for case in fixture.cases {
        assert!(case.cycle_inputs_available);
        let pose = RuntimePose {
            bone_addresses: case.bone_addresses,
            nodes: case
                .nodes
                .into_iter()
                .map(|n| {
                    (
                        n.address,
                        Node {
                            flags: n.flags,
                            world: n.world,
                            world_flags: n.world_flags,
                            parent: n.parent,
                            local: n.local.map(|l| (l, n.local_flags.unwrap())),
                        },
                    )
                })
                .collect(),
        };
        let records = case
            .cycle_records
            .into_iter()
            .map(|r| {
                let bytes: Vec<u8> = r
                    .state_hex
                    .as_bytes()
                    .chunks_exact(2)
                    .map(|p| u8::from_str_radix(std::str::from_utf8(p).unwrap(), 16).unwrap())
                    .collect();
                (
                    r.bone,
                    Record {
                        state: bytes.try_into().unwrap(),
                        record_flags: r.record_flags,
                    },
                )
            })
            .collect();
        let cycle = run(&pose, &records, &[case.requested_bone], case.delta, false).unwrap();
        assert_eq!(
            cycle.evaluation_order,
            vec![case.parent_modifier_bone, case.requested_bone]
        );
        assert_eq!(
            cycle.finalization_order,
            vec![case.requested_bone, case.parent_modifier_bone]
        );
        for expected in case.cycle_expected {
            let address = pose.bone_addresses[expected.bone];
            assert_eq!(
                cycle.finalized.runtime.nodes[&address].local,
                Some((expected.local, expected.local_flags))
            );
            assert_eq!(mode(&cycle.records[&expected.bone].state) & 0x10000000, 0);
            for (i, (a, b)) in cycle.finalized.published_worlds[&address]
                .0
                .iter()
                .zip(expected.world)
                .enumerate()
            {
                let error = (a - b).abs();
                maximum = maximum.max(error);
                if (12..15).contains(&i) {
                    maximum_position = maximum_position.max(error);
                } else {
                    maximum_basis = maximum_basis.max(error);
                }
                // Practical full-chain bound; writer-only fixture remains tighter.
                let tolerance = if (12..15).contains(&i) { 2e-5 } else { 2e-4 };
                assert!(
                    error <= tolerance,
                    "bone {} world element {i} error {error}",
                    expected.bone
                );
            }
        }
    }
    eprintln!("139 conditional parent-child cycles, maximum world error {maximum}; basis {maximum_basis}, position {maximum_position}");
}
