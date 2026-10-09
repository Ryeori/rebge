use super::*;
#[test]
#[ignore = "Private independent native transition tables"]
fn source_rules_match_native_records() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../reports/jade");
    let source: serde_json::Value = serde_json::from_slice(
        &std::fs::read(root.join("stage43-action-transition-decoded-20261009.json")).unwrap(),
    )
    .unwrap();
    let native: serde_json::Value = serde_json::from_slice(
        &std::fs::read(root.join("stage43-action-transition-tables-20261009-140854.json"))
            .unwrap(),
    )
    .unwrap();
    let mut checked = 0;
    for check in source["checks"].as_array().unwrap() {
        let tables: Vec<Table> = serde_json::from_value(
            source["actions"][check["key"].as_str().unwrap()]["tables"].clone(),
        )
        .unwrap();
        let action = native["actions"]
            .as_array()
            .unwrap()
            .iter()
            .find(|a| a["index"] == check["action_index"])
            .unwrap();
        let phase = action["descriptor"]["records"]
            .as_array()
            .unwrap()
            .iter()
            .find(|p| p["index"] == check["phase"])
            .unwrap();
        assert_eq!(phase["transition_table"]["unchanged"], true);
        for row in phase["transition_table"]["rows"].as_array().unwrap() {
            let expected: Rule = serde_json::from_value(row.clone()).unwrap();
            assert_eq!(
                lookup(
                    &tables,
                    check["phase"].as_u64().unwrap() as u8,
                    expected.requested
                ),
                Some(expected)
            );
            checked += 1;
        }
    }
    assert_eq!(checked, 64);
}
