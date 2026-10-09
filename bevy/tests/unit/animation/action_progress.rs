use super::*;
#[test]
#[ignore = "Private native action-switch snapshots"]
fn recorded_walk_phase_seek_channels() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../reports/jade/stage43-tracking-sequence-20261009-135516.json");
    let raw: serde_json::Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let sample = &raw["samples"][55];
    let tracks = sample["primary_clip"]["tracks"].as_array().unwrap();
    let seconds = tracks[0]["elapsed_seconds"].as_f64().unwrap() as f32;
    for track in tracks {
        if track["indexed_slot"].as_u64().unwrap() == 65535
            && track["track_flags"].as_u64().unwrap() & 0x8000 == 0
        {
            continue;
        }
        let clock = ClockTrack {
            frames: serde_json::from_value(track["frame_headers"].clone()).unwrap(),
            flags: track["track_flags"].as_u64().unwrap() as u16,
            auxiliary_short: track["auxiliary_short_u16"].as_u64().unwrap() as u16,
        };
        let state = seek(&clock, seconds, 1).unwrap();
        assert_eq!(state.index, track["frame_index"].as_u64().unwrap() as usize);
        assert!(
            (state.elapsed - track["elapsed_seconds"].as_f64().unwrap() as f32).abs() < 1e-7
        );
        assert_eq!(state.flags, track["state_flags"].as_u64().unwrap() as u16);
    }
    // Recorded master time validates relative channel seek, not VM request timing.
}
