use super::super::hierarchy::{IDENTITY, Node};
use super::*;
use serde::Deserialize;
#[derive(Deserialize)]
struct Operand {
    rotation: [f32; 4],
    position: Option<[f32; 3]>,
    reference: [f32; 16],
    reference_flags: u32,
    actor: [f32; 16],
    actor_flags: u32,
}
#[derive(Deserialize)]
struct Case {
    sample: usize,
    operands: Vec<Operand>,
    weight: Option<f32>,
    observed: [f32; 16],
    height: f32,
    add_height: bool,
}
#[derive(Deserialize)]
struct Fixture {
    cases: Vec<Case>,
}
#[test]
#[ignore = "Private conditional actor/reference and independent native slot0 outputs"]
fn recorded_complete_root_transition() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let rig: Skeleton = serde_json::from_slice(
        &std::fs::read(root.join("assets/skeletons/sally/gao-parent-links.json")).unwrap(),
    )
    .unwrap();
    let fixture: Fixture = serde_json::from_slice(
        &std::fs::read(root.join("reports/jade/stage43-root-transition-native.json")).unwrap(),
    )
    .unwrap();
    let bone = rig.objects.iter().position(|b| b.slot == Some(0)).unwrap();
    let mut maximum_basis = 0.0_f32;
    let mut maximum_position = 0.0_f32;
    let mut position_failures = Vec::new();
    let mut count = 0;
    for case in fixture.cases {
        let pose = RuntimePose {
            bone_addresses: (0..rig.objects.len()).map(|i| i as u64 + 10).collect(),
            nodes: BTreeMap::from([
                (
                    1,
                    Node {
                        flags: 0,
                        world: IDENTITY,
                        world_flags: 0,
                        parent: None,
                        local: None,
                    },
                ),
                (
                    bone as u64 + 10,
                    Node {
                        flags: 0x400000,
                        world: IDENTITY,
                        world_flags: 0,
                        parent: Some(1),
                        local: Some((IDENTITY, 0)),
                    },
                ),
            ]),
        };
        let contexts: Vec<_> = case
            .operands
            .iter()
            .map(|o| RootReferenceContext {
                actor_address: 1,
                actor_matrix: o.actor,
                actor_matrix_flags: o.actor_flags,
                reference_matrix: o.reference,
                reference_flags: o.reference_flags,
                height: case.height,
                add_height: case.add_height,
            })
            .collect();
        let writes: Vec<_> = case
            .operands
            .iter()
            .map(|o| LocalWrite {
                rotation: Some(o.rotation),
                position: o.position,
            })
            .collect();
        let outgoing = case.weight.map(|ratio| Outgoing {
            write: &writes[1],
            context: &contexts[1],
            ratio,
        });
        let result = apply(&pose, &rig, bone, &writes[0], &contexts[0], outgoing).unwrap();
        let actual = result.nodes[&(bone as u64 + 10)].local.unwrap().0;
        for i in [0, 1, 2, 4, 5, 6, 8, 9, 10] {
            let error = (actual[i] - case.observed[i]).abs();
            maximum_basis = maximum_basis.max(error);
            assert!(error <= 1e-5);
        }
        let error = (12..15)
            .map(|i| (actual[i] - case.observed[i]).abs())
            .fold(0., f32::max);
        maximum_position = maximum_position.max(error);
        if error > 1e-4 {
            position_failures.push((case.sample, error));
        }
        count += 1;
    }
    eprintln!(
        "{count} roots; basis max {maximum_basis}; position max {maximum_position}; position failures {position_failures:?}"
    );
    assert_eq!(count, 186);
    assert!(position_failures.is_empty());
}
