use super::*;

#[test]
#[ignore = "Requires private extracted Sally skeleton"]
fn extracted_sally_rig_links_and_animation_slots() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../assets/skeletons/sally/gao-parent-links.json");
    let rig: Skeleton = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    assert_eq!(rig.source_list, "7100AF2A");
    assert_eq!(rig.objects.len(), 48);
    let order = rig.topological_order().unwrap();
    assert_eq!(order.len(), 48);
    let slots: std::collections::BTreeSet<_> =
        rig.objects.iter().filter_map(|b| b.slot).collect();
    assert_eq!(slots, (0..47).collect());
    let mut broken: Skeleton = serde_json::from_slice(
        &std::fs::read(
            std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("../assets/skeletons/sally/gao-parent-links.json"),
        )
        .unwrap(),
    )
    .unwrap();
    broken.objects[0].linked_gao = Some(broken.objects[0].key.clone());
    assert!(broken.topological_order().is_err());
}
