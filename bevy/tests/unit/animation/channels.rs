use super::*;

#[test]
fn packed_signed_components_and_saturated_norm() {
    assert_eq!(packed_quaternion([0, 0, 0]), [0.0, 0.0, 0.0, 1.0]);
    assert_eq!(packed_quaternion([32767, 0, 0]), [1.0, 0.0, 0.0, 0.0]);
    assert_eq!(packed_quaternion([-32768, 0, 0])[3], 0.0);
}

#[derive(Deserialize)]
struct ChannelState {
    track_index: usize,
    index: usize,
    elapsed: f32,
}
#[derive(Deserialize)]
struct NativeSample {
    slot: u16,
    channels: Vec<ChannelState>,
    observed: [f32; 16],
}
#[derive(Deserialize)]
struct NativeFixture {
    source_key: String,
    cases: Vec<NativeSample>,
}

#[test]
#[ignore = "requires private exported walking channel fixture"]
fn recorded_walking_channels() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-bevy-walking-channels-native.json");
    let fixture: NativeFixture =
        serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    assert_eq!(fixture.cases.len(), 2880);
    let clip_path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join(format!(
        "../assets/animations/sally/local-samples/{}.json",
        fixture.source_key
    ));
    let clip: Clip =
        serde_json::from_str(&std::fs::read_to_string(clip_path).unwrap()).unwrap();
    for case in fixture.cases {
        for channel in case.channels {
            let track = &clip.tracks[channel.track_index];
            assert_eq!(track.short1, case.slot);
            if let Some(q) = sample_rotation(track, channel.index, channel.elapsed).unwrap() {
                let expected = super::super::pose_blend::quaternion_matrix(q);
                for i in [0, 1, 2, 4, 5, 6, 8, 9, 10] {
                    assert!((expected[i] - case.observed[i]).abs() <= 1e-5);
                }
            }
            if case.slot != 0 {
                if let Some(p) =
                    sample_translation(track, channel.index, channel.elapsed).unwrap()
                {
                    assert_eq!(p, [case.observed[12], case.observed[13], case.observed[14]]);
                }
            }
        }
    }
}
