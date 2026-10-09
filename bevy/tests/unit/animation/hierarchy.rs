use super::*;

fn nodes() -> BTreeMap<u64, Node> {
    let mut world = IDENTITY;
    world[12] = 10.;
    let mut local = IDENTITY;
    local[12] = 2.;
    BTreeMap::from([
        (
            1,
            Node {
                flags: 0x400001,
                world,
                world_flags: 2,
                parent: Some(2),
                local: Some((local, 2)),
            },
        ),
        (
            2,
            Node {
                flags: 0,
                world,
                world_flags: 2,
                parent: None,
                local: None,
            },
        ),
    ])
}

#[test]
fn linked_locals_override_stale_child_world_and_missing_parent_falls_back() {
    let mut nodes = nodes();
    assert_eq!(linked_target_position(&nodes, 1).unwrap(), [12., 0., 0.]);
    nodes.get_mut(&1).unwrap().parent = Some(0);
    assert_eq!(linked_target_position(&nodes, 1).unwrap(), [10., 0., 0.]);
}

#[test]
fn raw_basis_rotation_order_and_unsupported_scale() {
    let parent = [
        0., 1., 0., 0., -1., 0., 0., 0., 0., 0., 1., 0., 10., 20., 30., 1.,
    ];
    let mut local = IDENTITY;
    local[12..15].copy_from_slice(&[2., 3., 4.]);
    let (world, flags) = affine_product(&local, &parent, 0, 4).unwrap();
    assert_eq!(&world[12..15], &[7., 22., 34.]);
    assert_eq!(flags, 6);
    assert!(affine_product(&local, &parent, 8, 4).is_err());
    let mut nodes = nodes();
    nodes.get_mut(&1).unwrap().parent = Some(1);
    assert!(linked_target_position(&nodes, 1).is_err());
}
