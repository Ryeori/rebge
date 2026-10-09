use super::*;
#[derive(Deserialize)]
struct Case {
    deformation: Deformation,
    expected: Vec<[f32; 3]>,
}
#[derive(Deserialize)]
struct Palette {
    matrix: [f32; 16],
    flags: u32,
}
#[derive(Deserialize)]
struct Fixture {
    cases: Vec<Case>,
    palette: Vec<Palette>,
}
#[test]
#[ignore = "Private source meshes and Python numerical oracle; not GPU capture"]
fn source_geometry_python_oracle() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-cpu-skin-python-oracle.json");
    let fixture: Fixture = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let palette: Vec<_> = fixture
        .palette
        .iter()
        .map(|p| (p.matrix, p.flags))
        .collect();
    let mut count = 0;
    let mut maximum = 0.0_f32;
    for case in fixture.cases {
        let actual = deform(&case.deformation, &palette).unwrap();
        assert_eq!(actual.len(), case.expected.len());
        for (a, b) in actual.iter().zip(case.expected) {
            for i in 0..3 {
                let error = (a[i] - b[i]).abs();
                maximum = maximum.max(error);
                assert!(error <= 1e-5, "CPU skin error {error}");
            }
            count += 1;
        }
    }
    assert_eq!(count, 58218);
    eprintln!("{count} triangle vertices, CPU skin/Python maximum error {maximum}");
}
