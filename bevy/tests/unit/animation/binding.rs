use super::*;

#[test]
#[ignore = "Requires private extracted character assets"]
fn every_sally_clip_resolves_against_source_skeleton() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let rig: Skeleton = serde_json::from_slice(
        &std::fs::read(root.join("skeletons/sally/gao-parent-links.json")).unwrap(),
    )
    .unwrap();
    let mut binding: AnimationBinding = serde_json::from_slice(
        &std::fs::read(root.join("skeletons/sally/animation-binding.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(binding.resolve(&rig).unwrap().len(), 47);
    let mut count = 0;
    let mut special = 0;
    for entry in std::fs::read_dir(root.join("animations/sally/local-samples")).unwrap() {
        let path = entry.unwrap().path();
        if path.extension().and_then(|v| v.to_str()) != Some("json") {
            continue;
        }
        let clip: Clip = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
        let targets = binding.clip_targets(&rig, &clip).unwrap();
        assert_eq!(targets.len(), clip.tracks.len());
        special += targets
            .iter()
            .filter(|target| **target == TrackTarget::RootOrEvent)
            .count();
        count += 1;
    }
    assert_eq!(count, 214);
    assert!(special > 0);
    binding.slots[0].gao_key = binding.slots[1].gao_key.clone();
    assert!(binding.resolve(&rig).is_err());
}
