use super::*;
use serde::Deserialize;
#[derive(Deserialize)]
struct Node {
    address: u64,
    flags: u32,
    world: [f32; 16],
    world_flags: u32,
    parent: Option<u64>,
    local: Option<[f32; 16]>,
    local_flags: Option<u32>,
}
#[derive(Deserialize)]
struct State {
    track: usize,
    index: usize,
    elapsed: f32,
}
#[derive(Deserialize)]
struct Expected {
    bone: usize,
    local: [f32; 16],
}
#[derive(Deserialize)]
struct Case {
    keys: [String; 2],
    nodes: Vec<Node>,
    bone_addresses: Vec<u64>,
    outgoing: Vec<State>,
    primary: Vec<State>,
    ratio: f32,
    expected: Vec<Expected>,
}
#[derive(Deserialize)]
struct Fixture {
    cases: Vec<Case>,
}
#[test]
#[ignore = "Private original clips and qualified native blended locals"]
fn recorded_two_source_local_pipeline() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let read = |p: &str| std::fs::read(root.join(p)).unwrap();
    let rig: Skeleton =
        serde_json::from_slice(&read("assets/skeletons/sally/gao-parent-links.json")).unwrap();
    let binding: super::super::binding::AnimationBinding =
        serde_json::from_slice(&read("assets/skeletons/sally/animation-binding.json")).unwrap();
    let fixture: Fixture = serde_json::from_slice(&read(
        "reports/jade/stage43-transition-pipeline-native.json",
    ))
    .unwrap();
    let mut count = 0;
    let mut maximum = 0.0_f32;
    for case in fixture.cases {
        let pose = RuntimePose::new(
            &rig,
            case.bone_addresses,
            case.nodes
                .into_iter()
                .map(|n| {
                    (
                        n.address,
                        super::super::hierarchy::Node {
                            flags: n.flags,
                            world: n.world,
                            world_flags: n.world_flags,
                            parent: n.parent,
                            local: n.local.map(|m| (m, n.local_flags.unwrap())),
                        },
                    )
                })
                .collect(),
        )
        .unwrap();
        let sample = |key: &str, inputs: &[State]| {
            let clip: super::super::channels::Clip = serde_json::from_slice(&read(&format!(
                "assets/animations/sally/local-samples/{key}.json"
            )))
            .unwrap();
            let mut states = vec![None; clip.tracks.len()];
            for s in inputs {
                states[s.track] = Some(super::super::local_pose::TrackState {
                    index: s.index,
                    elapsed: s.elapsed,
                });
            }
            super::super::local_pose::sample_local_pose(&rig, &binding, &clip, &states).unwrap()
        };
        let outgoing = sample(&case.keys[0], &case.outgoing);
        let primary = sample(&case.keys[1], &case.primary);
        let bones = case.expected.iter().map(|e| e.bone).collect();
        let blended = apply(&pose, &rig, &outgoing, &primary, &bones, case.ratio).unwrap();
        for expected in case.expected {
            let local = blended.nodes[&blended.bone_addresses[expected.bone]]
                .local
                .unwrap()
                .0;
            for i in [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14] {
                let error = (local[i] - expected.local[i]).abs();
                maximum = maximum.max(error);
                assert!(error <= 1e-5, "bone {} element {i}: {error}", expected.bone);
            }
            count += 1;
        }
    }
    assert_eq!(count, 646);
    eprintln!("646 source-channel to native transition locals; maximum error {maximum}");
}
