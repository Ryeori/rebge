use super::*;
#[test]
#[ignore = "Private independent native R2 start input timelines and locomotion bank"]
fn recorded_run_start_inputs_preserve_native_chain() {
    let project = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let root = project.join("assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(&root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json")).unwrap(),
        root, screenshot: None, localization: String::new(), exit_after_capture: false,
    };
    for run in ["run_held_start-original-r1-20261010-014908",
                "run_to_walk-original-r1-20261010-015015"] {
        let record: serde_json::Value = serde_json::from_slice(&std::fs::read(project.join(
            format!("reports/jade/movement-suite/{run}/run.json"))).unwrap()).unwrap();
        let points = record["case"]["points"].as_array().unwrap();
        let mut p = load(&source).unwrap().unwrap();
        let world = p.pose.nodes[&p.seed.actor_address].world;
        p.control_direction = Vec3::new(-world[4], -world[5], 0.).normalize();
        let mut chain = vec![p.control_phase];
        for frame in 0..75 {
            let t = frame as f64 / 60.;
            let point = points.iter().rev().find(|x| x["t"].as_f64().unwrap() <= t).unwrap();
            p.run_requested = point["r2"].as_f64().unwrap_or(0.) > 0.;
            let x = point["x"].as_f64().unwrap() as f32;
            let y = point["y"].as_f64().unwrap() as f32;
            p.input_strength = (x*x + y*y).sqrt();
            p.request_move(p.input_strength > 0.).unwrap();
            p.step(1./60., &source).unwrap();
            if chain.last() != Some(&p.control_phase) {
                if p.control_phase == ControlPhase::Walking {
                    assert_eq!(p.seed.transition.as_ref().unwrap().duration_byte, 15,
                        "native Slow1 -> Walking3 blend row");
                }
                chain.push(p.control_phase);
            }
        }
        assert_eq!(chain, vec![ControlPhase::WaitingIdle, ControlPhase::Slow,
            ControlPhase::Walking, ControlPhase::Running], "{run}");
    }
}
#[test]
#[ignore = "Private locomotion bank; held sprint start and post-turn acceleration"]
fn preview_held_run_preserves_walk_and_accelerates() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(
            &root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json"),
        )
        .unwrap(),
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    for after_turn in [false, true] {
        for strength in [1., 0.6] {
            let mut p = load(&source).unwrap().unwrap();
            p.select(
                if after_turn {
                    ControlPhase::TurningA
                } else {
                    ControlPhase::Idle
                },
                false,
            )
            .unwrap();
            let world = p.pose.nodes[&p.seed.actor_address].world;
            let forward = Vec3::new(-world[4], -world[5], 0.).normalize();
            p.control_direction = if after_turn { -forward } else { forward };
            p.run_requested = true;
            p.input_strength = strength;
            p.request_move(true).unwrap();
            let mut walking_frames = 0;
            let mut saw_starting = false;
            let mut speeds = Vec::new();
            for _ in 0..200 {
                saw_starting |= p.control_phase == ControlPhase::Starting;
                let running = p.control_phase == ControlPhase::Running;
                if p.control_phase == ControlPhase::Walking && speeds.is_empty() {
                    walking_frames += 1;
                }
                let old = p.pose.nodes[&p.seed.actor_address].world;
                p.step(1. / 60., &source).unwrap();
                let new = p.pose.nodes[&p.seed.actor_address].world;
                if running {
                    speeds.push(
                        Vec3::new(new[12] - old[12], new[13] - old[13], new[14] - old[14])
                            .length()
                            * 60.,
                    );
                    if speeds.len() == 48 {
                        break;
                    }
                }
            }
            assert!(
                if after_turn { walking_frames == 0 } else { walking_frames >= 12 },
                "walking stage skipped after_turn={after_turn}, frames={walking_frames}"
            );
            assert_eq!(speeds.len(), 48);
            assert!(!saw_starting, "held sprint used mode1 Starting4 after_turn={after_turn}");
            let settled = speeds[45..].iter().sum::<f32>() / 3.;
            println!(
                "ACCEL after_turn={after_turn} walking_frames={walking_frames} initial={} settled={settled}",
                speeds[0]
            );
            assert!(
                if after_turn { speeds[0] <= settled * 1.05 } else { speeds[0] < settled * 0.8 },
                "instant full running speed after_turn={after_turn}"
            );
            assert!(speeds.iter().all(|s| s.is_finite()));
        }
    }
}
#[test]
#[ignore = "Private native long-run stop recording; phase durations and idle completion"]
fn recorded_long_run_stop_phase_timing() {
    let project = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let root = project.join("assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(&root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json")).unwrap(),
        root, screenshot: None, localization: String::new(), exit_after_capture: false,
    };
    let raw: serde_json::Value = serde_json::from_slice(&std::fs::read(project.join(
        "reports/jade/stage43-tracking-sequence-20261009-213501.json")).unwrap()).unwrap();
    let samples = raw["samples"].as_array().unwrap();
    let a = samples.iter().position(|s| s["current_action_index_a8"] == 53
        && s["current_phase_index"] == 0).unwrap();
    let b = samples.iter().position(|s| s["current_action_index_a8"] == 53
        && s["current_phase_index"] == 1).unwrap();
    let idle = (b+1..samples.len()).find(|&i| samples[i]["current_action_index_a8"] == 0).unwrap();
    let origin = samples[a]["elapsed_seconds"].as_f64().unwrap();
    let observed_b = (samples[b]["elapsed_seconds"].as_f64().unwrap()-origin) as f32;
    let observed_idle = (samples[idle]["elapsed_seconds"].as_f64().unwrap()-origin) as f32;
    let mut p = load(&source).unwrap().unwrap();
    p.select(ControlPhase::Running, false).unwrap();
    p.action_phase = 1;
    p.input_strength = 0.;
    p.request_move(false).unwrap();
    assert_eq!(p.control_phase, ControlPhase::RunStoppingA);
    assert_eq!(p.seed.speed, 56);
    let mut elapsed = 0.;
    let mut second = None;
    while p.control_phase != ControlPhase::Idle && elapsed < 2. {
        p.step(1./60., &source).unwrap();
        elapsed += 1./60.;
        if p.control_phase == ControlPhase::RunStoppingB && second.is_none() {
            second = Some(elapsed);
        }
    }
    let second = second.expect("No second long-run stopping phase");
    println!("STOP53 preview_b={second} native_b={observed_b} preview_idle={elapsed} native_idle={observed_idle}");
    assert!((second-observed_b).abs() < 0.04);
    assert_eq!(p.control_phase, ControlPhase::Idle);
    assert!((elapsed-observed_idle).abs() < 0.04);
}
#[test]
#[ignore = "Private preview bank; walk to sprint speed continuity"]
fn preview_walk_run_acceleration_continuity() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(&root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json")).unwrap(),
        root, screenshot: None, localization: String::new(), exit_after_capture: false,
    };
    let mut global_max = 0f32;
    for hold in [65, 95, 125, 155] {
        let mut p = load(&source).unwrap().unwrap();
        let world = p.pose.nodes[&p.seed.actor_address].world;
        p.control_direction = Vec3::new(-world[4], -world[5], 0.).normalize();
        p.request_move(true).unwrap();
        let mut previous_speed: Option<f32> = None;
        let mut maximum = 0f32;
        for frame in 0..hold+50 {
            p.run_requested = frame >= hold;
            let before = p.pose.nodes[&p.seed.actor_address].world;
            p.step(1./60., &source).unwrap();
            let after = p.pose.nodes[&p.seed.actor_address].world;
            let speed = Vec3::new(after[12]-before[12], after[13]-before[13],
                after[14]-before[14]).length()*60.;
            if frame >= hold && let Some(previous) = previous_speed {
                let change = (speed-previous).abs();
                maximum = maximum.max(change);
                if frame < hold+8 { println!("WALKRUN hold={hold} frame={} speed={speed} change={change}",frame-hold); }
            }
            previous_speed = Some(speed);
        }
        println!("WALKRUN hold={hold} maximum_speed_step={maximum}");
        global_max = global_max.max(maximum);
    }
    assert!(global_max < 0.25, "walk/run speed step {global_max}");
}
#[test]
#[ignore = "Private preview bank; terminal exit root continuity into sprint"]
fn preview_postturn_run_does_not_pull_back() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(&root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json")).unwrap(),
        root, screenshot: None, localization: String::new(), exit_after_capture: false,
    };
    for hz in [30, 60, 120] {
        let mut p = load(&source).unwrap().unwrap();
        let world = p.pose.nodes[&p.seed.actor_address].world;
        let forward = Vec3::new(-world[4], -world[5], 0.).normalize();
        p.control_direction = forward;
        p.move_requested = true;
        p.run_requested = true;
        p.input_strength = 1.;
        p.joy_value = 1.;
        p.select(ControlPhase::TurnWalk, false).unwrap();
        p.seed.speed = 61;
        let mut previous: Option<Vec<(usize, Vec<[f32; 3]>)>> = None;
        let mut worst_back = 0f32;
        for frame in 0..hz * 2 {
            let actor_before = p.pose.nodes[&p.seed.actor_address].world;
            let vertices = p.step(1. / hz as f32, &source).unwrap();
            if let Some(old) = &previous {
                let mut mean = Vec3::ZERO;
                let mut count = 0f32;
                for ((_, a), (_, b)) in old.iter().zip(&vertices) {
                    for (a, b) in a.iter().zip(b) {
                        mean += Vec3::from_array(*b) - Vec3::from_array(*a);
                        count += 1.;
                    }
                }
                if p.control_phase == ControlPhase::Running
                    && p.seed.transition.as_ref().is_some_and(|t| t.active)
                {
                    let rendered_forward = Vec3::from_array(jade_to_bevy(&forward.to_array())).normalize();
                    let displacement = (mean / count).dot(rendered_forward);
                    if displacement < -0.01 {
                        let actor_after = p.pose.nodes[&p.seed.actor_address].world;
                        let actor_delta = Vec3::new(actor_after[12]-actor_before[12],
                            actor_after[13]-actor_before[13], actor_after[14]-actor_before[14]).dot(forward);
                        println!("BACK hz={hz} frame={frame} centroid={displacement} actor={actor_delta} blend={:?}",
                            p.seed.transition.as_ref().map(|t| (t.active,t.ratio)));
                    }
                    worst_back = worst_back.max(-displacement);
                }
            }
            previous = Some(vertices);
        }
        println!("POSTTURN hz={hz} maximum_backward_centroid={worst_back}");
        assert!(worst_back < 0.02, "post-turn body pulled back hz={hz}: {worst_back}");
    }
}
#[test]
#[ignore = "Private independent native no-sprint80 speed and completion recording"]
fn recorded_no_sprint_turn_exit_speed_and_completion() {
    let project = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let root = project.join("assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(&root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json")).unwrap(),
        root, screenshot: None, localization: String::new(), exit_after_capture: false,
    };
    let raw: serde_json::Value = serde_json::from_slice(&std::fs::read(project.join(
        "reports/jade/stage43-tracking-sequence-20261010-004413.json")).unwrap()).unwrap();
    let samples = raw["samples"].as_array().unwrap();
    let entry = samples.iter().position(|s| s["current_action_index_a8"] == 80).unwrap();
    let end = (entry + 1..samples.len()).find(|&i| samples[i]["current_action_index_a8"] != 80).unwrap();
    assert_eq!(samples[end]["current_action_index_a8"], 3);
    let observed_duration = (samples[end]["elapsed_seconds"].as_f64().unwrap()
        - samples[entry]["elapsed_seconds"].as_f64().unwrap()) as f32;
    let mut p = load(&source).unwrap().unwrap();
    p.move_requested = true;
    p.input_strength = 1.;
    p.joy_value = 1.;
    let world = p.pose.nodes[&p.seed.actor_address].world;
    p.control_direction = Vec3::new(-world[4], -world[5], 0.).normalize();
    p.select(ControlPhase::TurnWalk, false).unwrap();
    // Entry primary header60 is observed separately from the still-79
    // brain snapshot. Do not treat their sequential read as atomic order.
    assert_eq!(samples[entry]["primary_header_unchanged"], true);
    assert_eq!(p.seed.speed as u64, samples[entry]["primary_speed_byte"].as_u64().unwrap());
    let mut qualified_speeds = Vec::new();
    for sample in &samples[entry + 1..end] {
        let writer = &sample["speed_writer_inputs"];
        if writer["unchanged"] != true || sample["primary_header_unchanged"] != true
            || sample["primary_states_unchanged"] != true || sample["pose_matrices_unchanged"] != true {
            continue;
        }
        let hex = writer["state_10c4_hex"].as_str().unwrap();
        let bytes: Vec<_> = (0..hex.len()).step_by(2)
            .map(|i| u8::from_str_radix(&hex[i..i + 2], 16).unwrap()).collect();
        let word = |offset| i32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap());
        assert_eq!(word(0), 80);
        assert_eq!(word(0x2c), 80);
        assert_eq!(word(0x20), 2);
        assert_eq!(word(0x28), word(0x30));
        let observed_speed = sample["primary_speed_byte"].as_u64().unwrap() as u8;
        assert_eq!(observed_speed, crate::input::animation_speed::quantize(word(0x34)));
        qualified_speeds.push(observed_speed);
    }
    assert!(qualified_speeds.len() >= 10);
    let mut elapsed = 0.;
    while p.control_phase == ControlPhase::TurnWalk && elapsed < 1.2 {
        let vertices = p.step(1. / 60., &source).unwrap();
        elapsed += 1. / 60.;
        assert!(vertices.iter().flat_map(|(_, mesh)| mesh).flatten().all(|v| v.is_finite()));
        if p.control_phase == ControlPhase::TurnWalk {
            assert!(qualified_speeds.iter().all(|speed| *speed == p.seed.speed));
        }
    }
    assert_eq!(p.control_phase, ControlPhase::Walking);
    // One sampled native boundary and one preview frame limit the timing
    // claim; this is source-clock duration validation, not pose parity.
    println!("NO_SPRINT_EXIT native_duration={observed_duration} preview_duration={elapsed} stable_speed_samples={}", qualified_speeds.len());
    assert!((elapsed - observed_duration).abs() < 0.05,
        "No-sprint80 completion differs from independent native recording");
    assert_eq!(p.seed.speed, p.seed.controls.as_ref().unwrap().walk.speed,
        "No-sprint80 speed must not leak into newly bound Walking3");
}
#[test]
#[ignore = "Private independent native post-turn traces and runtime transition table"]
fn recorded_postturn_exit_and_incoming_run() {
    let project = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let source = Source {
        root: project.join("assets"),
        scene: crate::assets::scene::load_scene(
            &project.join("assets"),
            std::path::Path::new("scenes/sally-playback/controlled-scene.json"),
        ).unwrap(),
        screenshot: None, localization: String::new(), exit_after_capture: false,
    };
    let native: serde_json::Value = serde_json::from_slice(&std::fs::read(
        project.join("reports/jade/stage43-action-transition-tables-20261009-210821.json")
    ).unwrap()).unwrap();
    let incoming = native["actions"].as_array().unwrap().iter()
        .find(|a| a["index"] == 2).unwrap()["descriptor"]["records"][0]
        ["transition_table"]["rows"].as_array().unwrap().iter()
        .find(|r| r["requested"] == 2).unwrap().clone();
    assert_eq!(incoming["record_unchanged"], true);
    for stamp in ["205707", "210317", "210516", "210624"] {
        let raw: serde_json::Value = serde_json::from_slice(&std::fs::read(project.join(
            format!("reports/jade/stage43-tracking-sequence-20261009-{stamp}.json")
        )).unwrap()).unwrap();
        let samples = raw["samples"].as_array().unwrap();
        let exit = samples.iter().position(|s| s["current_action_index_a8"] == 80).unwrap();
        let run = (exit+1..samples.len()).find(|&i| samples[i]["current_action_index_a8"] != 80).unwrap();
        assert_eq!(samples[run]["current_action_index_a8"], 2);
        let observed = (samples[run]["elapsed_seconds"].as_f64().unwrap()
            - samples[exit]["elapsed_seconds"].as_f64().unwrap()) as f32;
        let mut p = load(&source).unwrap().unwrap();
        p.run_requested = true;
        p.move_requested = true;
        p.input_strength = 1.;
        p.joy_value = 1.;
        p.select(ControlPhase::TurnWalk, false).unwrap();
        p.seed.speed = p.seed.controls.as_ref().unwrap().run.as_ref().unwrap().clip.speed;
        let mut elapsed = 0.;
        while p.control_phase == ControlPhase::TurnWalk && elapsed < 1. {
            p.step(1. / 60., &source).unwrap();
            elapsed += 1. / 60.;
        }
        assert_eq!(p.control_phase, ControlPhase::Running);
        assert!((elapsed-observed).abs() < 0.04, "native{stamp}: preview{elapsed} observed{observed}");
        assert_eq!(p.seed.speed, samples[run]["primary_speed_byte"].as_u64().unwrap() as u8);
        assert_eq!(p.seed.transition.as_ref().unwrap().duration_byte,
            incoming["duration_byte"].as_u64().unwrap() as u8);
        assert!(p.run_from_turn);
    }
}
#[test]
#[ignore = "Private bank; preview continuous reverse from initial running phase"]
fn preview_running_reverse_uses_stop_then_turn() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(
            &root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json"),
        )
        .unwrap(),
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    for phase in [0, 1] {
        let mut p = load(&source).unwrap().unwrap();
        p.select(ControlPhase::Running, false).unwrap();
        p.action_phase = phase;
        let world = p.pose.nodes[&p.seed.actor_address].world;
        let forward = Vec3::new(-world[4], -world[5], 0.).normalize();
        p.move_requested = true;
        p.run_requested = true;
        p.joy_value = 1.;
        p.control_direction = forward;
        for _ in 0..10 {
            p.step(1. / 60., &source).unwrap();
        }
        p.control_direction = -forward;
        p.step(1. / 60., &source).unwrap();
        assert_eq!(
            p.control_phase,
            if phase == 0 {
                ControlPhase::StoppingA
            } else {
                ControlPhase::RunStoppingA
            }
        );
        p.step(1. / 60., &source).unwrap();
        assert_eq!(p.control_phase, ControlPhase::TurningA);
        let mut saw_b = false;
        for _ in 0..120 {
            let vertices = p.step(1. / 60., &source).unwrap();
            assert!(
                vertices
                    .iter()
                    .flat_map(|(_, v)| v)
                    .flatten()
                    .all(|v| v.is_finite())
            );
            saw_b |= p.control_phase == ControlPhase::TurningB;
        }
        assert!(saw_b);
        assert_eq!(p.control_phase, ControlPhase::Running);
    }
}
#[test]
#[ignore = "Private bank; running stop interrupted by renewed/opposite input"]
fn preview_run_stop_reentry_continuity() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(
            &root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json"),
        )
        .unwrap(),
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    for hold in [65, 245] {
        for gap in [1, 3, 7, 13, 20] {
            for reverse in [false, true] {
                let mut p = load(&source).unwrap().unwrap();
                let world = p.pose.nodes[&p.seed.actor_address].world;
                let forward = Vec3::new(-world[4], -world[5], 0.).normalize();
                p.control_direction = forward;
                p.run_requested = true;
                p.request_move(true).unwrap();
                for _ in 0..hold {
                    p.step(1. / 60., &source).unwrap();
                }
                let mut old: Option<Vec<(usize, Vec<[f32; 3]>)>> = None;
                let mut maximum = 0f32;
                for frame in 0..(gap + 90) {
                    let moving = frame >= gap;
                    p.run_requested = false;
                    p.input_strength = if moving { 1. } else { 0. };
                    p.control_direction = if moving && reverse { -forward } else { forward };
                    p.request_move(moving).unwrap();
                    let vertices = p.step(1. / 60., &source).unwrap();
                    if let Some(old) = &old {
                        let mut mean = Vec3::ZERO;
                        let mut count = 0f32;
                        for ((_, a), (_, b)) in old.iter().zip(&vertices) {
                            for (a, b) in a.iter().zip(b) {
                                let d = Vec3::from_array(*b) - Vec3::from_array(*a);
                                mean += d;
                                count += 1.;
                                maximum = maximum.max(d.length());
                            }
                        }
                        assert!(
                            (mean / count).length() < 0.3,
                            "reentry body jump hold={hold} gap={gap} reverse={reverse} frame={frame} delta={}",
                            (mean / count).length()
                        );
                    }
                    old = Some(vertices);
                }
                println!(
                    "REENTRY hold={hold} gap={gap} reverse={reverse} maximum_vertex_delta={maximum}"
                );
                assert!(maximum < 0.8, "reentry pose jump {maximum}");
                assert_eq!(p.control_phase, ControlPhase::Walking);
            }
        }
    }
}
#[test]
#[ignore = "Private bank; weak reverse rebound during stick release"]
fn preview_run_release_ignores_weak_reverse_input() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(
            &root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json"),
        )
        .unwrap(),
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    for hold in [65, 95, 125, 155, 185, 215, 245, 275] {
        let mut p = load(&source).unwrap().unwrap();
        let world = p.pose.nodes[&p.seed.actor_address].world;
        let forward = Vec3::new(-world[4], -world[5], 0.).normalize();
        p.control_direction = forward;
        p.run_requested = true;
        p.request_move(true).unwrap();
        for _ in 0..hold {
            p.step(1. / 60., &source).unwrap();
        }
        p.run_requested = false;
        p.input_strength = 0.;
        p.request_move(false).unwrap();
        p.step(1. / 60., &source).unwrap();
        for strength in [0.2, 0.18, 0., 0.] {
            p.input_strength = strength;
            p.control_direction = if strength > 0. { -forward } else { Vec3::ZERO };
            p.request_move(strength > 0.).unwrap();
            p.step(1. / 60., &source).unwrap();
            assert!(
                !matches!(
                    p.control_phase,
                    ControlPhase::TurningA
                        | ControlPhase::TurningB
                        | ControlPhase::StandingNegative
                        | ControlPhase::StandingPositive
                ),
                "weak release rebound triggered {:?}, hold={hold}",
                p.control_phase
            );
        }
    }
}
#[test]
#[ignore = "Private assets; repeated abrupt run/walk/stop input diagnostic"]
fn preview_repeated_gait_inputs() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(
            &root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json"),
        )
        .unwrap(),
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    for stop in [false, true] {
        let mut p = load(&source).unwrap().unwrap();
        let world = p.pose.nodes[&p.seed.actor_address].world;
        p.control_direction = Vec3::new(-world[4], -world[5], 0.).normalize();
        let mut old: Option<Vec<(usize, Vec<[f32; 3]>)>> = None;
        let mut maximum = 0f32;
        let mut prior_actor = Vec3::ZERO;
        let mut prior_root = Vec3::ZERO;
        for (cycle, hold) in [65, 95, 125, 155, 185, 215, 245, 275]
            .into_iter()
            .enumerate()
        {
            for frame in 0..(hold + 100) {
                p.run_requested = frame < hold;
                p.input_strength = if p.run_requested { 1. } else { 0.4 };
                p.request_move(p.run_requested || !stop).unwrap();
                let before = p.control_phase;
                let cycles_before = p.clip_cycles;
                let blend_should_survive = p.seed.transition.as_ref().is_some_and(|b|
                    b.active && (b.duration_byte as f32 + 1.) / 60.
                        - b.elapsed_u16 as f32 / 15360. > 1. / 60.);
                let vertices = p.step(1. / 60., &source).unwrap();
                if before == ControlPhase::Walking && p.control_phase == before
                    && p.clip_cycles > cycles_before && blend_should_survive {
                    assert!(p.seed.transition.as_ref().is_some_and(|b| b.active),
                        "same-action phase bind erased active incoming blend");
                }
                let actor = p.pose.nodes[&p.seed.actor_address].world;
                let actor_position = Vec3::new(actor[12], actor[13], actor[14]);
                let root_index = p
                    .seed
                    .rig
                    .objects
                    .iter()
                    .position(|b| b.slot == Some(0))
                    .unwrap();
                let root_world = p.pose.nodes[&p.pose.bone_addresses[root_index]].world;
                let root_position = Vec3::new(root_world[12], root_world[13], root_world[14]);
                if let Some(old) = &old {
                    let jump = old
                        .iter()
                        .zip(&vertices)
                        .flat_map(|((_, a), (_, b))| a.iter().zip(b))
                        .map(|(a, b)| Vec3::from_array(*a).distance(Vec3::from_array(*b)))
                        .fold(0f32, f32::max);
                    if jump > maximum {
                        maximum = jump;
                        let mut displacement = Vec3::ZERO;
                        let mut count = 0.;
                        for ((_, a), (_, b)) in old.iter().zip(&vertices) {
                            for (a, b) in a.iter().zip(b) {
                                displacement += Vec3::from_array(*b) - Vec3::from_array(*a);
                                count += 1.;
                            }
                        }
                        assert!(
                            (displacement / count).length() < 0.15,
                            "whole-body jump {before:?}->{:?}, cycle={cycle}, frame={frame}, centroid={}, actor={}",
                            p.control_phase, (displacement / count).length(),
                            actor_position.distance(prior_actor)
                        );
                        println!(
                            "REPEAT stop={stop} cycle={cycle} frame={frame} phase={before:?}->{:?} vertex_delta={jump} actor_delta={} root_delta={} centroid_delta={}",
                            p.control_phase,
                            actor_position.distance(prior_actor),
                            root_position.distance(prior_root),
                            (displacement / count).length()
                        );
                    }
                    if !stop && cycle == 1 && frame == 11 {
                        let displacement: Vec3 = old.iter().zip(&vertices)
                            .flat_map(|((_, a), (_, b))| a.iter().zip(b))
                            .map(|(a,b)| Vec3::from_array(*b)-Vec3::from_array(*a)).sum();
                        let count: usize = old.iter().map(|(_,a)| a.len()).sum();
                        println!("REGRESSION cycle1 frame11 vertex={jump} centroid={} blend_active={}",
                            (displacement / count as f32).length(),
                            p.seed.transition.as_ref().is_some_and(|b| b.active));
                    }
                }
                old = Some(vertices);
                prior_actor = actor_position;
                prior_root = root_position;
            }
        }
        // Limb speed is phase dependent; the centroid bound above detects
        // whole-body jumps separately from rapid but continuous limb motion.
        assert!(maximum < 0.5, "repeated gait discontinuity: {maximum}");
    }
}
#[test]
#[ignore = "Private source standing-turn bank; preview trigger and completion"]
fn preview_standing_opposite_input() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(
            &root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json"),
        )
        .unwrap(),
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    for side in [-0.2f32, 0.2] {
        let mut p = load(&source).unwrap().unwrap();
        p.select(ControlPhase::Idle, false).unwrap();
        let world = p.pose.nodes[&p.seed.actor_address].world;
        let forward = Vec3::new(-world[4], -world[5], 0.).normalize();
        let perpendicular = Vec3::new(-forward.y, forward.x, 0.);
        p.control_direction = (-forward + side * perpendicular).normalize();
        p.request_move(true).unwrap();
        let expected = if side < 0. {
            ControlPhase::StandingNegative
        } else {
            ControlPhase::StandingPositive
        };
        assert_eq!(p.control_phase, expected);
        for _ in 0..20 {
            p.step(1. / 60., &source).unwrap();
        }
        assert_eq!(p.control_phase, expected);
        let turned = p.pose.nodes[&p.seed.actor_address].world;
        let heading = Vec3::new(-turned[4], -turned[5], 0.).normalize();
        assert!(
            forward.cross(heading).z * side > 0.,
            "source turn direction disagrees with requested side"
        );
        for _ in 0..60 {
            p.step(1. / 60., &source).unwrap();
        }
        assert!(!matches!(
            p.control_phase,
            ControlPhase::StandingNegative | ControlPhase::StandingPositive
        ));
        assert!(
            p.pose.nodes[&p.seed.actor_address]
                .world
                .iter()
                .all(|v| v.is_finite())
        );
        p.select(ControlPhase::Idle, false).unwrap();
        let world = p.pose.nodes[&p.seed.actor_address].world;
        p.control_direction = Vec3::new(world[4], world[5], 0.).normalize();
        p.request_move(true).unwrap();
        for _ in 0..15 {
            p.step(1. / 60., &source).unwrap();
        }
        p.request_move(false).unwrap();
        assert!(matches!(p.control_phase,
            ControlPhase::StandingNegative | ControlPhase::StandingPositive));
        for _ in 0..60 {
            p.step(1. / 60., &source).unwrap();
        }
        assert!(matches!(p.control_phase, ControlPhase::Idle | ControlPhase::WaitingIdle));
    }
}
#[test]
#[ignore = "Private independent native standing pulse recording; release and completion timing"]
fn recorded_standing_release_finishes_rotation() {
    let project = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let root = project.join("assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(&root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json")).unwrap(),
        root, screenshot: None, localization: String::new(), exit_after_capture: false,
    };
    let raw: serde_json::Value = serde_json::from_slice(&std::fs::read(project.join(
        "reports/jade/stage43-tracking-sequence-20261009-215901.json")).unwrap()).unwrap();
    let samples = raw["samples"].as_array().unwrap();
    let mut cases = 0;
    let rows: serde_json::Value = serde_json::from_slice(&std::fs::read(project.join(
        "reports/jade/stage43-action-transition-tables-20261009-221038.json")).unwrap()).unwrap();
    for i in 1..samples.len() {
        let action = samples[i]["current_action_index_a8"].as_u64().unwrap();
        if !matches!(action, 116 | 117)
            || samples[i-1]["current_action_index_a8"] == action { continue; }
        let end = (i+1..samples.len()).find(|&j|
            samples[j]["current_action_index_a8"] != action).unwrap();
        assert_eq!(samples[end]["current_action_index_a8"], 0);
        let observed = (samples[end]["elapsed_seconds"].as_f64().unwrap()
            - samples[i]["elapsed_seconds"].as_f64().unwrap()) as f32;
        let phase = if action == 116 { ControlPhase::StandingNegative }
            else { ControlPhase::StandingPositive };
        for hz in [30., 60., 120.] {
            let mut p = load(&source).unwrap().unwrap();
            p.move_requested = true;
            p.select(phase, false).unwrap();
            let initial = p.pose.nodes[&p.seed.actor_address].world;
            let forward = Vec3::new(-initial[4], -initial[5], 0.).normalize();
            let mut elapsed = 0.;
            while elapsed < 0.12 {
                p.step(1./hz, &source).unwrap();
                elapsed += 1./hz;
            }
            p.request_move(false).unwrap();
            assert_eq!(p.control_phase, phase, "Early release interrupted source rotation");
            while p.control_phase == phase && elapsed < 1. {
                p.step(1./hz, &source).unwrap();
                elapsed += 1./hz;
            }
            assert_eq!(p.control_phase, ControlPhase::Idle);
            let table = rows["actions"].as_array().unwrap().iter()
                .find(|r| r["index"] == action).unwrap();
            let native_row = table["descriptor"]["records"][0]["transition_table"]["rows"]
                .as_array().unwrap().iter().find(|r| r["requested"] == 0).unwrap();
            assert_eq!(native_row["flags"], 0);
            assert_eq!(native_row["record_unchanged"], true);
            let outgoing = p.seed.transition.as_ref().expect("Missing standing to idle blend");
            assert!(outgoing.active);
            assert_eq!(outgoing.duration_byte as u64, native_row["duration_byte"].as_u64().unwrap());
            assert!(outgoing.interrupted_pose.is_some(), "Terminal standing pose must not loop during blend");
            println!("STANDING action={action} sample={i} hz={hz} native={observed} preview={elapsed}");
            assert!((elapsed-observed).abs() < 0.05,
                "Standing completion differs from independent native pulse");
            let world = p.pose.nodes[&p.seed.actor_address].world;
            let heading = Vec3::new(-world[4], -world[5], 0.).normalize();
            assert!(forward.dot(heading) < -0.95, "Released turn lost its opposite heading");
        }
        cases += 1;
    }
    assert_eq!(cases, 4);
}
#[test]
#[ignore = "Private assets; walking blend pending-request regression, not native parity"]
fn walking_blend_preserves_qualified_moving_turn() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(&root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json")).unwrap(),
        root, screenshot: None, localization: String::new(), exit_after_capture: false,
    };
    for (strength, release) in [(1., false), (1., true), (0.5, false)] {
        let mut p = load(&source).unwrap().unwrap();
        p.select(ControlPhase::Walking, false).unwrap();
        let world = p.pose.nodes[&p.seed.actor_address].world;
        p.control_direction = Vec3::new(-world[4], -world[5], 0.).normalize();
        p.input_strength = 1.;
        p.request_move(true).unwrap();
        for _ in 0..60 { p.step(1. / 60., &source).unwrap(); }
        p.select_at_duration(ControlPhase::Walking, true, None, Some(6)).unwrap();
        assert!(p.seed.transition.as_ref().unwrap().active);
        let world = p.pose.nodes[&p.seed.actor_address].world;
        p.control_direction = Vec3::new(world[4], world[5], 0.).normalize();
        p.input_strength = strength;
        p.request_move(true).unwrap();
        p.step(1. / 60., &source).unwrap();
        assert_eq!(p.control_phase, ControlPhase::Walking);
        assert_eq!(p.pending_moving_turn, strength >= 0.6);
        if strength < 0.6 {
            // Normalized weak input must not latch a full-strength reversal.
            continue;
        }
        if release {
            p.input_strength = 0.;
            p.control_direction = Vec3::ZERO;
            p.request_move(false).unwrap();
            assert!(p.pending_moving_turn, "Chosen request survives release while waiting for blend");
        }
        let mut previous_phase = p.control_phase;
        let mut entries = 0;
        let mut last_turn_elapsed = None;
        let mut reached_second_phase = false;
        for _ in 0..120 {
            let before = p.pose.nodes[&p.seed.actor_address].world;
            let vertices = p.step(1. / 60., &source).unwrap();
            let after = p.pose.nodes[&p.seed.actor_address].world;
            assert!(after.iter().all(|v| v.is_finite()));
            assert!(vertices.iter().flat_map(|(_, mesh)| mesh).flatten().all(|v| v.is_finite()));
            assert!(Vec3::from_array(before[12..15].try_into().unwrap())
                .distance(Vec3::from_array(after[12..15].try_into().unwrap())) < 0.3);
            for root in p.seed.root.iter().chain(p.seed.transition.iter().filter_map(|t| t.root.as_ref())) {
                assert!(root.reference.iter().all(|v| v.is_finite()));
            }
            if p.control_phase == ControlPhase::TurningA {
                if previous_phase != ControlPhase::TurningA { entries += 1; }
                assert!(!p.pending_moving_turn);
                let elapsed = p.seed.actor_motion.as_ref().unwrap().tracks[0].state.elapsed;
                if let Some(last) = last_turn_elapsed {
                    assert!(elapsed >= last, "Source-owned turn restarted");
                }
                last_turn_elapsed = Some(elapsed);
            }
            if p.control_phase == ControlPhase::TurningB {
                reached_second_phase = true;
                break;
            }
            previous_phase = p.control_phase;
        }
        assert_eq!(entries, 1);
        assert!(reached_second_phase, "Queued walking turn must dispatch and continue source phase");
    }
}
#[test]
#[ignore = "Private independent short reversal input timelines and branch observations"]
fn recorded_short_reversal_branch_family() {
    let project = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let root = project.join("assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(&root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json")).unwrap(),
        root, screenshot: None, localization: String::new(), exit_after_capture: false,
    };
    let fixture: serde_json::Value = serde_json::from_slice(&std::fs::read(project.join(
        "reports/jade/movement-suite/native-short-reversal-fixture-20261010.json")).unwrap()).unwrap();
    let cases = fixture["cases"].as_array().unwrap();
    assert_eq!(cases.len(), 4);
    for case in cases {
        let vector = |value: &serde_json::Value| Vec3::new(value[0].as_f64().unwrap() as f32,
            value[1].as_f64().unwrap() as f32, value[2].as_f64().unwrap() as f32);
        let mut p = load(&source).unwrap().unwrap();
        let world = p.pose.nodes[&p.seed.actor_address].world;
        let forward = Vec3::new(-world[4], -world[5], 0.);
        let measured_forward = vector(&case["initial_case_input"]["forward"]);
        let rotation = measured_forward.y.atan2(measured_forward.x) - forward.y.atan2(forward.x);
        let pivot = world[12..15].try_into().unwrap();
        let actor = p.pose.nodes.get_mut(&p.seed.actor_address).unwrap();
        crate::input::diagnostic_steering::rotate(&mut actor.world, pivot, rotation);
        actor.world_flags &= !1;
        if let Some(root) = &mut p.seed.root {
            crate::input::diagnostic_steering::rotate(&mut root.reference, pivot, rotation);
            root.reference_flags &= !1;
        }
        let initial_direction = vector(&case["initial_case_input"]["direction"]);
        let opposite_direction = vector(&case["first_qualified_opposite"]["direction"]);
        let timeline = case["timeline"].as_array().unwrap();
        let mut index = 0;
        let mut active = None;
        let mut observed_family = None;
        for frame in 0..150 {
            let t = frame as f32 / 60.;
            while index < timeline.len() && timeline[index]["t"].as_f64().unwrap() <= t as f64 {
                active = Some(&timeline[index]); index += 1;
            }
            let x = active.map_or(0., |row| row["x"].as_f64().unwrap() as f32);
            p.input_strength = crate::input::stick::movement_stick(Vec2::new(x, 0.)).length();
            // Command publication precedes native polling. Camera mapping
            // holds the independently observed initial/opposite directions;
            // only branch family is compared, not side/pose/frame timing.
            p.control_direction = if p.input_strength == 0. { Vec3::ZERO }
                else if x < 0. { initial_direction } else { opposite_direction };
            let before = p.pose.nodes[&p.seed.actor_address].world;
            p.request_move(p.input_strength > 0.).unwrap();
            let vertices = p.step(1. / 60., &source).unwrap();
            let after = p.pose.nodes[&p.seed.actor_address].world;
            assert!(after.iter().all(|v| v.is_finite()));
            assert!(vertices.iter().flat_map(|(_, mesh)| mesh).flatten().all(|v| v.is_finite()));
            assert!(Vec3::from_array(before[12..15].try_into().unwrap())
                .distance(Vec3::from_array(after[12..15].try_into().unwrap())) < 0.3);
            observed_family = match p.control_phase {
                ControlPhase::StandingNegative | ControlPhase::StandingPositive => Some("standing116_117"),
                ControlPhase::TurningA | ControlPhase::TurningB => Some("moving79"),
                _ => observed_family,
            };
            if observed_family.is_some() { break; }
        }
        println!("SHORT_BRANCH case={} native={} preview={observed_family:?} last_qualified_turn_speed_proxy={:?}",
            case["case"], case["expected_branch_family"], p.last_turn_candidate_speed);
        assert_eq!(observed_family, case["expected_branch_family"].as_str(),
            "Independent short-input timeline selected another branch family");
    }
}
#[test]
#[ignore = "Private independent geometry/input recordings; continuity diagnostic, not parity"]
fn independent_geometry_replay_continuity() {
    let project = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let root = project.join("assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(&root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json")).unwrap(),
        root, screenshot: None, localization: String::new(), exit_after_capture: false,
    };
    let fixtures: Vec<serde_json::Value> = [
        "reports/jade/movement-suite/native-standing-delivery-replay-20261010.json",
        "reports/jade/movement-suite/native-standing-delivery-r1-r2-replay-20261010.json",
    ].iter().map(|path| serde_json::from_slice(&std::fs::read(project.join(path)).unwrap()).unwrap()).collect();
    let cases: Vec<_> = fixtures.iter().flat_map(|fixture| fixture["cases"].as_array().unwrap()).collect();
    assert_eq!(cases.len(), 5);
    let mut reports = Vec::new();
    for case in cases {
        let vector = |value: &serde_json::Value| Vec3::new(
            value[0].as_f64().unwrap() as f32,
            value[1].as_f64().unwrap() as f32,
            value[2].as_f64().unwrap() as f32,
        );
        let mut p = load(&source).unwrap().unwrap();
        p.select(ControlPhase::WaitingIdle, false).unwrap();
        if let Some(response) = case["observed_initial_response1198"].as_f64() {
            p.slow_heading_response = response as f32;
        }
        let world = p.pose.nodes[&p.seed.actor_address].world;
        let forward = Vec3::new(-world[4], -world[5], 0.).normalize();
        let initial = vector(&case["initial_geometry"]["forward"]);
        let rotation = initial.y.atan2(initial.x) - forward.y.atan2(forward.x);
        let pivot = world[12..15].try_into().unwrap();
        let actor = p.pose.nodes.get_mut(&p.seed.actor_address).unwrap();
        crate::input::diagnostic_steering::rotate(&mut actor.world, pivot, rotation);
        actor.world_flags &= !1;
        if let Some(root) = &mut p.seed.root {
            crate::input::diagnostic_steering::rotate(&mut root.reference, pivot, rotation);
            root.reference_flags &= !1;
        }
        if let Some(root) = p.seed.transition.as_mut().and_then(|t| t.root.as_mut()) {
            crate::input::diagnostic_steering::rotate(&mut root.reference, pivot, rotation);
            root.reference_flags &= !1;
        }
        let rows = case["rows"].as_array().unwrap();
        let observed_rows = case["independently_observed_rows"].as_array().unwrap();
        let mut row_index = 0;
        let mut active_row = None;
        let mut seen = false;
        let mut seen_phases = Vec::new();
        let mut maximum_position_delta = 0f32;
        let mut frames = Vec::new();
        let duration = case["duration"].as_f64().unwrap() as f32;
        for frame in 0..=(duration * 60.).ceil() as usize {
            let t = frame as f32 / 60.;
            // Dense command norm uses a modeled native component gate;
            // camera world direction is interpolated from separate native
            // observations. These are delivered-input approximations.
            while row_index < rows.len() && rows[row_index]["t"].as_f64().unwrap() <= t as f64 {
                active_row = Some(&rows[row_index]);
                row_index += 1;
            }
            p.input_strength = active_row.map_or(0., |row| row["norm"].as_f64().unwrap() as f32);
            p.control_direction = active_row.map_or(Vec3::ZERO, |row| vector(&row["direction"]));
            let before = p.pose.nodes[&p.seed.actor_address].world;
            p.request_move(p.input_strength > 0.).unwrap();
            let vertices = p.step(1. / 60., &source).unwrap();
            let after = p.pose.nodes[&p.seed.actor_address].world;
            assert!(after.iter().all(|value| value.is_finite()));
            assert!(vertices.iter().flat_map(|(_, mesh)| mesh).flatten().all(|v| v.is_finite()));
            let distance = Vec3::from_array(before[12..15].try_into().unwrap())
                .distance(Vec3::from_array(after[12..15].try_into().unwrap()));
            maximum_position_delta = maximum_position_delta.max(distance);
            assert!(distance < 0.3, "Replay actor discontinuity: {} t={t} distance={distance}", case["case"]);
            seen |= matches!(p.control_phase, ControlPhase::StandingNegative | ControlPhase::StandingPositive);
            let phase = format!("{:?}", p.control_phase);
            if seen_phases.last() != Some(&phase) {
                seen_phases.push(phase.clone());
            }
            let native_hint = observed_rows.iter().take_while(|row|
                row["t"].as_f64().unwrap() <= t as f64).last();
            let heading = Vec3::new(-after[4], -after[5], 0.).normalize_or_zero();
            frames.push(serde_json::json!({
                "t":t,"phase":phase,
                "heading":heading.to_array(),"input_strength":p.input_strength,
                "direction":p.control_direction.to_array(),"position_delta":distance,
                "native_action_hint":native_hint.map(|row| &row["action"]),
                "native_forward_hint":native_hint.map(|row| &row["forward"]),
                "native_hint_t":native_hint.map(|row| &row["t"]),
            }));
        }
        let native_observed = observed_rows.iter().any(|row| matches!(row["action"].as_u64(), Some(116 | 117)));
        println!("DELIVERY_REPLAY case={} source={} native_actions={} preview_phases={seen_phases:?} native_turn={native_observed} preview_turn={seen} max_position_delta={maximum_position_delta}",
            case["case"], case["source"], case["expected_action_sequence"]);
        // Measured heading is evidence, never reset into the evolving actor.
        // Selection agreement is reported, not asserted: scheduling and the
        // preview velocity feeding ordinary steering remain approximate.
        reports.push(serde_json::json!({
            "case":case["case"],"source":case["source"],"source_sha256":case["source_sha256"],
            "native_expected_actions":case["expected_action_sequence"],"preview_seen_phases":seen_phases,
            "observed_initial_response1198":case["observed_initial_response1198"],
            "initial_response1198_provenance":case["initial_response1198_provenance"],
            "native_observed_turn":native_observed,"preview_seen_turn":seen,
            "maximum_position_delta":maximum_position_delta,"frames":frames,
        }));
    }
    std::fs::write(project.join("reports/bevy/independent-delivery-replay-continuity-20261010.json"),
        serde_json::to_vec_pretty(&serde_json::json!({
            "schema":"preview-independent-delivery-replay-diagnostic-v1","cases":reports,
            "limits":fixtures.iter().map(|fixture| &fixture["limits"]).collect::<Vec<_>>(),
            "claim":"Continuity only; command gate and camera mapping are approximations, native selection and heading parity are not asserted.",
        })).unwrap()).unwrap();
}
#[test]
#[ignore = "Private assets; gait-change continuity diagnostic"]
fn preview_gait_change_continuity() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(
            &root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json"),
        )
        .unwrap(),
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    for hold in [15, 25, 35, 45, 55, 65] {
        let mut p = load(&source).unwrap().unwrap();
        let world = p.pose.nodes[&p.seed.actor_address].world;
        p.control_direction = Vec3::new(-world[4], -world[5], 0.).normalize();
        p.request_move(true).unwrap();
        for _ in 0..100 {
            p.step(1. / 60., &source).unwrap();
        }
        p.run_requested = true;
        let mut old = None;
        let mut maximum = 0f32;
        for frame in 0..(hold + 80) {
            if frame == hold {
                p.run_requested = false;
                p.input_strength = 0.4;
            }
            let vertices = p.step(1. / 60., &source).unwrap();
            if let Some(old) = &old {
                let old: &Vec<(usize, Vec<[f32; 3]>)> = old;
                let jump = old
                    .iter()
                    .zip(&vertices)
                    .flat_map(|((_, a), (_, b))| a.iter().zip(b))
                    .map(|(a, b)| Vec3::from_array(*a).distance(Vec3::from_array(*b)))
                    .fold(0f32, f32::max);
                if jump > maximum {
                    maximum = jump;
                }
            }
            old = Some(vertices);
        }
        assert_eq!(p.control_phase, ControlPhase::Slow);
        assert!(maximum < 0.3, "gait-change discontinuity: {maximum}");
        println!("GAIT hold={hold} maximum_vertex_delta={maximum}");
    }
}
#[test]
#[ignore = "Private restart bank; low-input phase progression diagnostic"]
fn preview_restart_second_phase_completes_queued_slow() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(
            &root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json"),
        )
        .unwrap(),
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    let mut player = load(&source).unwrap().unwrap();
    player.select(ControlPhase::Restart, false).unwrap();
    player.queued_action = Some(1);
    player.move_requested = true;
    player.input_strength = 0.4;
    player.joy_value = 0.4;
    let mut reached_second = false;
    for _ in 0..120 {
        // Supply a low input scalar explicitly; analog frontend is separate.
        let before = player.pose.nodes[&player.seed.actor_address].world;
        let vertices = player.step(1. / 60., &source).unwrap();
        assert!(
            vertices
                .iter()
                .flat_map(|(_, v)| v)
                .flatten()
                .all(|v| v.is_finite())
        );
        let after = player.pose.nodes[&player.seed.actor_address].world;
        assert!(
            Vec3::from_array(before[12..15].try_into().unwrap())
                .distance(Vec3::from_array(after[12..15].try_into().unwrap()))
                < 0.3
        );
        reached_second |= player.control_phase == ControlPhase::RestartSecond;
        if reached_second && player.control_phase == ControlPhase::Slow {
            break;
        }
    }
    assert!(reached_second);
    assert_eq!(player.control_phase, ControlPhase::Slow);
    assert_eq!(player.queued_action, None);
}
#[test]
#[ignore = "Private locomotion bank; preview running integration, not full native parity"]
fn preview_walk_run_switch_and_stop() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(
            &root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json"),
        )
        .unwrap(),
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    for release_running in [false, true] {
        let mut player = load(&source).unwrap().unwrap();
        let world = player.pose.nodes[&player.seed.actor_address].world;
        player.control_direction = Vec3::new(-world[4], -world[5], 0.).normalize();
        player.request_move(true).unwrap();
        for _ in 0..100 {
            player.step(1. / 60., &source).unwrap();
        }
        assert_eq!(player.control_phase, ControlPhase::Walking);
        player.run_requested = true;
        let mut reached_second = false;
        for _ in 0..240 {
            let before = player.pose.nodes[&player.seed.actor_address].world;
            let vertices = player.step(1. / 60., &source).unwrap();
            assert!(
                vertices
                    .iter()
                    .flat_map(|(_, v)| v)
                    .flatten()
                    .all(|v| v.is_finite())
            );
            let after = player.pose.nodes[&player.seed.actor_address].world;
            assert!(
                Vec3::from_array(before[12..15].try_into().unwrap())
                    .distance(Vec3::from_array(after[12..15].try_into().unwrap()))
                    < 0.3
            );
            reached_second |= player.action_phase == 1;
        }
        assert_eq!(player.control_phase, ControlPhase::Running);
        assert!(
            reached_second,
            "Run descriptor did not reach looping phase1"
        );
        if release_running {
            player.request_move(false).unwrap();
        } else {
            player.run_requested = false;
            for _ in 0..45 {
                player.step(1. / 60., &source).unwrap();
            }
            assert_eq!(player.control_phase, ControlPhase::Walking);
            player.request_move(false).unwrap();
        }
        for _ in 0..120 {
            player.step(1. / 60., &source).unwrap();
        }
        assert!(matches!(
            player.control_phase,
            ControlPhase::Idle | ControlPhase::WaitingIdle
        ));
    }
}
#[test]
#[ignore = "Private assets; abrupt-input diagnostic, not native parity"]
fn preview_abrupt_direction_diagnostic() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(
            &root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json"),
        )
        .unwrap(),
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    for (interval, hz) in [
        (3, 60),
        (7, 60),
        (15, 60),
        (30, 60),
        (60, 60),
        (60, 120),
        (120, 240),
    ] {
        let mut player = load(&source).unwrap().unwrap();
        let world = player.pose.nodes[&player.seed.actor_address].world;
        let forward = Vec3::new(-world[4], -world[5], 0.).normalize();
        let side = Vec3::new(-forward.y, forward.x, 0.);
        let directions = [forward, -forward, side, -side];
        let mut max_actor = 0f32;
        let mut max_vertex = 0f32;
        let mut previous: Option<Vec<(usize, Vec<[f32; 3]>)>> = None;
        for frame in 0..(hz * 4) {
            let warmup = hz * 5 / 3;
            player.control_direction = if frame < warmup {
                forward
            } else {
                directions[((frame - warmup) / interval) % 4]
            };
            player.request_move(true).unwrap();
            let before = player.pose.nodes[&player.seed.actor_address].world;
            let phase = player.control_phase;
            let previous_nodes = player.pose.nodes.clone();
            let vertices = player.step(1. / hz as f32, &source).unwrap();
            let after = player.pose.nodes[&player.seed.actor_address].world;
            let distance = Vec3::from_array(before[12..15].try_into().unwrap())
                .distance(Vec3::from_array(after[12..15].try_into().unwrap()));
            if distance > max_actor {
                max_actor = distance;
                println!(
                    "interval={interval} frame={frame} actor_delta={distance} phase={phase:?}->{:?}",
                    player.control_phase
                );
            }
            if let Some(old) = &previous {
                for ((_, a), (_, b)) in old.iter().zip(&vertices) {
                    let distance = a
                        .iter()
                        .zip(b)
                        .map(|(a, b)| Vec3::from_array(*a).distance(Vec3::from_array(*b)))
                        .fold(0f32, f32::max);
                    if distance > max_vertex {
                        max_vertex = distance;
                        if distance > 0.3 {
                            println!(
                                "VERTEX interval={interval} frame={frame} delta={distance} phase={phase:?}->{:?}",
                                player.control_phase
                            );
                            if hz == 120 {
                                for (bone, address) in
                                    player.pose.bone_addresses.iter().enumerate()
                                {
                                    if let (Some((a, _)), Some((b, _))) = (
                                        previous_nodes[address].local,
                                        player.pose.nodes[address].local,
                                    ) {
                                        let change = a
                                            .iter()
                                            .zip(b)
                                            .map(|(a, b)| (a - b).abs())
                                            .fold(0f32, f32::max);
                                        if change > 0.2 {
                                            println!(
                                                "LOCAL bone={bone} delta={change} components={:?}",
                                                a.iter()
                                                    .zip(b)
                                                    .enumerate()
                                                    .filter(|(_, (a, b))| (*a - *b).abs() > 0.2)
                                                    .collect::<Vec<_>>()
                                            );
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            assert!(
                vertices
                    .iter()
                    .flat_map(|(_, v)| v)
                    .flatten()
                    .all(|x| x.is_finite())
            );
            previous = Some(vertices);
        }
        println!(
            "ABRUPT hz={hz} interval={interval} max_actor={max_actor} max_vertex={max_vertex}"
        );
        // Diagnostic continuity bound scales with the integration step;
        // the old loop-wrap jump grew to 0.9 even at 240Hz.
        assert!(
            max_vertex < 0.3 * 60. / hz as f32,
            "Discontinuous preview pose at {hz}Hz: {max_vertex}"
        );
    }
}
#[test]
#[ignore = "Private reverse clips; preview scheduling and continuity, not native VM parity"]
fn preview_reverse_uses_source_rotation_and_both_exits() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let source = Source {
        scene: crate::assets::scene::load_scene(
            &root,
            std::path::Path::new("scenes/sally-playback/controlled-scene.json"),
        )
        .unwrap(),
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    for release in [false, true] {
        let mut player = load(&source).unwrap().unwrap();
        player.request_move(true).unwrap();
        let initial = player.pose.nodes[&player.seed.actor_address].world;
        let forward = Vec3::new(-initial[4], -initial[5], 0.).normalize();
        player.control_direction = forward;
        for _ in 0..100 {
            player.step(1. / 60., &source).unwrap();
        }
        assert_eq!(player.control_phase, ControlPhase::Walking);
        player.control_direction = -forward;
        // Real keyboard reversal may contain a short zero-input gap.
        player.request_move(false).unwrap();
        for _ in 0..2 {
            player.step(1. / 60., &source).unwrap();
        }
        player.request_move(true).unwrap();
        let mut phases = Vec::new();
        for frame in 0..150 {
            if release && frame == 10 {
                player.request_move(false).unwrap();
            }
            let before = player.pose.nodes[&player.seed.actor_address].world;
            let vertices = player.step(1. / 60., &source).unwrap();
            assert!(
                vertices
                    .iter()
                    .flat_map(|(_, v)| v)
                    .flatten()
                    .all(|x| x.is_finite())
            );
            let after = player.pose.nodes[&player.seed.actor_address].world;
            if matches!(
                player.control_phase,
                ControlPhase::TurnStop | ControlPhase::TurnWalk
            ) {
                assert!(
                    Vec3::new(-after[4], -after[5], 0.)
                        .normalize()
                        .dot(-forward)
                        > 0.95,
                    "Source reverse rotation did not reach opposite heading"
                );
            }
            let jump = Vec3::from_array(before[12..15].try_into().unwrap())
                .distance(Vec3::from_array(after[12..15].try_into().unwrap()));
            assert!(jump < 0.3, "reverse frame{frame} jump{jump}");
            if phases.last() != Some(&player.control_phase) {
                phases.push(player.control_phase);
            }
        }
        assert!(phases.contains(&ControlPhase::TurningA));
        assert!(phases.contains(&ControlPhase::TurningB));
        assert!(phases.contains(&if release {
            ControlPhase::TurnStop
        } else {
            ControlPhase::TurnWalk
        }));
        if release {
            assert!(matches!(
                player.control_phase,
                ControlPhase::Idle | ControlPhase::WaitingIdle
            ));
        } else {
            assert_eq!(player.control_phase, ControlPhase::Walking);
            let world = player.pose.nodes[&player.seed.actor_address].world;
            assert!(
                Vec3::new(-world[4], -world[5], 0.)
                    .normalize()
                    .dot(-forward)
                    > 0.95
            );
        }
    }
}
#[test]
#[ignore = "Private original clips and actor scene"]
fn preview_steering_preserves_root_continuation() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let scene = crate::assets::scene::load_scene(
        &root,
        std::path::Path::new("scenes/sally-playback/controlled-scene.json"),
    )
    .unwrap();
    let source = Source {
        scene,
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    let mut player = load(&source).unwrap().unwrap();
    player.request_move(true).unwrap();
    let initial = player.pose.nodes[&player.seed.actor_address].world;
    player.control_direction = Vec3::new(-initial[4], -initial[5], 0.).normalize();
    for _ in 0..90 {
        player.step(1. / 60., &source).unwrap();
    }
    assert_eq!(player.control_phase, ControlPhase::Walking);
    let before = player.pose.nodes[&player.seed.actor_address].world;
    let first_position = Vec3::from_array(before[12..15].try_into().unwrap());
    player.control_direction =
        Vec3::new(-player.control_direction.y, player.control_direction.x, 0.);
    for _ in 0..90 {
        let previous = player.pose.nodes[&player.seed.actor_address].world;
        let vertices = player.step(1. / 60., &source).unwrap();
        assert!(
            vertices
                .iter()
                .flat_map(|(_, points)| points)
                .flatten()
                .all(|x| x.is_finite())
        );
        let current = player.pose.nodes[&player.seed.actor_address].world;
        let distance = Vec3::from_array(current[12..15].try_into().unwrap())
            .distance(Vec3::from_array(previous[12..15].try_into().unwrap()));
        assert!(distance < 0.3, "Reference jump during turn:{distance}");
    }
    let after = player.pose.nodes[&player.seed.actor_address].world;
    let heading = Vec3::new(-after[4], -after[5], 0.).normalize();
    assert!(heading.dot(player.control_direction) > 0.99);
    assert!(Vec3::from_array(after[12..15].try_into().unwrap()).distance(first_position) > 1.);
    player.control_direction = Vec3::ZERO;
    player.request_move(false).unwrap();
    for _ in 0..90 {
        player.step(1. / 60., &source).unwrap();
    }
    assert!(matches!(
        player.control_phase,
        ControlPhase::Idle | ControlPhase::WaitingIdle
    ));
}
#[test]
#[ignore = "Private phase/repeat boundary captures and original clip bank"]
fn native_phase_boundaries_carry_in_viewer() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let scene = crate::assets::scene::load_scene(
        &root,
        std::path::Path::new("scenes/sally-playback/controlled-scene.json"),
    )
    .unwrap();
    let source = Source {
        scene,
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    let raw: serde_json::Value = serde_json::from_slice(
        &std::fs::read(
            std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("../reports/jade/stage43-tracking-sequence-20261008-183132.json"),
        )
        .unwrap(),
    )
    .unwrap();
    let repeat_raw: serde_json::Value = serde_json::from_slice(
        &std::fs::read(
            std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("../reports/jade/stage43-tracking-sequence-20261009-030317.json"),
        )
        .unwrap(),
    )
    .unwrap();
    let queued_raw: serde_json::Value = serde_json::from_slice(
        &std::fs::read(
            std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("../reports/jade/stage43-tracking-sequence-20261009-150304.json"),
        )
        .unwrap(),
    )
    .unwrap();
    let waiting_raw: serde_json::Value = serde_json::from_slice(
        &std::fs::read(
            std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("../reports/jade/stage43-tracking-sequence-20261009-152531.json"),
        )
        .unwrap(),
    )
    .unwrap();
    for (sequence, a, b, phase, repeat) in [
        (&raw, 63, 64, ControlPhase::StoppingA, 0),
        (&raw, 242, 243, ControlPhase::Walking, 0),
        (&repeat_raw, 23, 24, ControlPhase::Walking, 0),
        (&repeat_raw, 74, 75, ControlPhase::Walking, 1),
        (&repeat_raw, 124, 125, ControlPhase::Walking, 2),
        (&repeat_raw, 174, 175, ControlPhase::Walking, 3),
        (&queued_raw, 206, 207, ControlPhase::StoppingB, 0),
        (&waiting_raw, 187, 188, ControlPhase::Idle, 0),
    ] {
        let before = &sequence["samples"][a];
        let after = &sequence["samples"][b];
        let native_state = |t: &serde_json::Value| ClockState {
            index: t["frame_index"].as_u64().unwrap() as usize,
            elapsed: t["elapsed_seconds"].as_f64().unwrap() as f32,
            flags: t["state_flags"].as_u64().unwrap() as u16,
        };
        let mut player = load(&source).unwrap().unwrap();
        player.select(phase, false).unwrap();
        // Recorded walking boundaries occurred with forward input held.
        player.move_requested = phase == ControlPhase::Walking;
        player.action_phase = before["current_phase_index"].as_u64().unwrap() as u8;
        player.action_repeat = repeat;
        if phase == ControlPhase::Idle {
            let decode = |value: &serde_json::Value| {
                let hex = value.as_str().unwrap();
                let bytes: Vec<u8> = (0..8)
                    .step_by(2)
                    .map(|i| u8::from_str_radix(&hex[i..i + 2], 16).unwrap())
                    .collect();
                f32::from_le_bytes(bytes.try_into().unwrap())
            };
            let context = &before["stationary_selector_inputs"];
            player.scene_time = decode(&context["globals_hex"]["0x1420a3310"]);
            player.idle_action_time = decode(&context["brain_hex"]["0x7b8"]);
        }
        if phase == ControlPhase::StoppingB {
            player.queued_action = Some(0);
        }
        for t in &mut player.seed.tracks {
            t.state = native_state(&before["primary_clip"]["tracks"][t.index]);
        }
        for t in &mut player.seed.root.as_mut().unwrap().tracks {
            t.state = native_state(&before["primary_clip"]["tracks"][t.index]);
        }
        for t in &mut player.seed.actor_motion.as_mut().unwrap().tracks {
            t.state = native_state(&before["primary_clip"]["tracks"][t.index]);
        }
        player
            .step(after["delta_time"].as_f64().unwrap() as f32, &source)
            .unwrap();
        assert_eq!(
            player.control_phase,
            if phase == ControlPhase::Idle {
                assert_eq!(player.seed.transition.as_ref().unwrap().duration_byte, 20);
                ControlPhase::WaitingIdle
            } else if phase == ControlPhase::StoppingB {
                assert_eq!(player.queued_action, None);
                assert!(player.seed.transition.is_none());
                ControlPhase::Idle
            } else if phase == ControlPhase::Walking {
                ControlPhase::Walking
            } else {
                ControlPhase::StoppingB
            }
        );
        assert_eq!(
            player.action_phase,
            after["current_phase_index"].as_u64().unwrap() as u8
        );
        if a != 63 && a != 242 && a != 206 && a != 187 {
            assert_eq!(player.action_repeat, repeat + 1);
        }
        for t in player
            .seed
            .actor_motion
            .as_ref()
            .unwrap()
            .tracks
            .iter()
            .chain(&player.seed.root.as_ref().unwrap().tracks)
            .chain(&player.seed.tracks)
        {
            let expected = native_state(&after["primary_clip"]["tracks"][t.index]);
            assert_eq!(
                (t.state.index, t.state.elapsed, t.state.flags),
                (expected.index, expected.elapsed, expected.flags),
                "{a}->{b} track {}",
                t.index
            );
        }
    }
    // Clock agreement does not establish the captured full pose/reference.
}
#[test]
#[ignore = "Private source clip, runtime seed and skin geometry"]
fn diagnostic_runs_multiple_clip_loops() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let scene = crate::assets::scene::load_scene(
        &root,
        std::path::Path::new("scenes/sally-playback/scene.json"),
    )
    .unwrap();
    let source = Source {
        scene,
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    let mut player = load(&source).unwrap().unwrap();
    let initial = player.step(0., &source).unwrap();
    let mut moved = false;
    for _ in 0..600 {
        let current = player.step(1. / 60., &source).unwrap();
        moved |= current.iter().zip(&initial).any(|((_, a), (_, b))| a != b);
    }
    assert!(moved);
    assert!(!player.stopped);
}
#[test]
#[ignore = "Private two-clip transition scene and native seed"]
fn diagnostic_transition_completes_and_primary_continues() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let scene = crate::assets::scene::load_scene(
        &root,
        std::path::Path::new("scenes/sally-playback/transition-scene.json"),
    )
    .unwrap();
    let source = Source {
        scene,
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    let mut player = load(&source).unwrap().unwrap();
    assert!(player.seed.transition.as_ref().unwrap().active);
    let mut ratios = Vec::new();
    let mut complete = false;
    for _ in 0..120 {
        player.step(1. / 60., &source).unwrap();
        let state = player.seed.transition.as_ref().unwrap();
        if state.active {
            ratios.push(state.ratio);
        } else {
            complete = true;
        }
    }
    assert!(complete && !ratios.is_empty());
    assert!(ratios.windows(2).all(|w| w[1] > w[0]));
    assert!(ratios.iter().all(|r| *r >= 0. && *r < 1.));
}
#[test]
#[ignore = "Private source-root motion scene and native reference seed"]
fn diagnostic_root_motion_repeats_and_blends() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let scene = crate::assets::scene::load_scene(
        &root,
        std::path::Path::new("scenes/sally-playback/root-motion-scene.json"),
    )
    .unwrap();
    let source = Source {
        scene,
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    let mut player = load(&source).unwrap().unwrap();
    for _ in 0..600 {
        player.step(1. / 60., &source).unwrap();
    }
    let actor = player.pose.nodes[&player.seed.actor_address].world;
    let displacement: Vec<_> = (0..3)
        .map(|i| actor[12 + i] - player.motion_origin[i])
        .collect();
    eprintln!(
        "Root motion: {} shared completions, displacement {displacement:?}",
        player.root_cycles
    );
    assert!(player.root_cycles >= 10);
    assert!(displacement.iter().map(|x| x * x).sum::<f32>() > 1.);
    assert!(!player.seed.transition.as_ref().unwrap().active);
}
#[test]
#[ignore = "Private original clip bank; provisional input scheduling, not native VM parity"]
fn controlled_press_release_and_interruptions() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../assets");
    let scene = crate::assets::scene::load_scene(
        &root,
        std::path::Path::new("scenes/sally-playback/controlled-scene.json"),
    )
    .unwrap();
    let source = Source {
        scene,
        root,
        screenshot: None,
        localization: String::new(),
        exit_after_capture: false,
    };
    let mut player = load(&source).unwrap().unwrap();
    assert_eq!(player.control_phase, ControlPhase::WaitingIdle);
    for _ in 0..15 {
        player.step(1. / 60., &source).unwrap();
    }
    player.request_move(true).unwrap();
    assert_eq!(player.control_phase, ControlPhase::Slow);
    player.step(1. / 60., &source).unwrap();
    player.request_move(false).unwrap();
    assert_eq!(player.control_phase, ControlPhase::Slow);
    for _ in 0..10 {
        player.step(1. / 60., &source).unwrap();
    }
    assert_eq!(player.control_phase, ControlPhase::Idle);
    assert_eq!(player.seed.transition.as_ref().unwrap().duration_byte, 10);
    player = load(&source).unwrap().unwrap();
    player.request_move(true).unwrap();
    let mut saw_start = false;
    for _ in 0..35 {
        player.step(1. / 60., &source).unwrap();
        saw_start |= player.control_phase == ControlPhase::Starting;
    }
    assert!(saw_start);
    assert_eq!(player.control_phase, ControlPhase::Walking);
    player.request_move(false).unwrap();
    assert_eq!(player.control_phase, ControlPhase::Idle);
    for _ in 0..15 {
        player.step(1. / 60., &source).unwrap();
    }
    player.request_move(true).unwrap();
    assert_eq!(player.control_phase, ControlPhase::Restart);
    assert_eq!(player.queued_action, Some(1));
    let native_restart: serde_json::Value = serde_json::from_slice(
        &std::fs::read(
            std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("../reports/jade/stage43-tracking-sequence-20261009-152034.json"),
        )
        .unwrap(),
    )
    .unwrap();
    let observed = &native_restart["samples"][116];
    assert_eq!(observed["action_selection_unchanged"], true);
    assert_eq!(observed["current_action_index_a8"], 51);
    assert_eq!(
        player.queued_action.unwrap() as u64,
        observed["requested_action_index_aa"].as_u64().unwrap()
    );
    let native_header = observed["transition_header_hex"].as_str().unwrap();
    let native_duration = u8::from_str_radix(&native_header[0x59 * 2..0x5a * 2], 16).unwrap();
    assert_eq!(
        player.seed.transition.as_ref().unwrap().duration_byte,
        native_duration
    );
    for _ in 0..30 {
        if player.control_phase == ControlPhase::Walking {
            break;
        }
        player.step(1. / 60., &source).unwrap();
    }
    assert_eq!(player.control_phase, ControlPhase::Walking);
    assert_eq!(player.action_phase, 0);
    player.request_move(false).unwrap();
    assert_eq!(player.control_phase, ControlPhase::Walking);
    for _ in 0..15 {
        player.step(1. / 60., &source).unwrap();
    }
    assert_eq!(player.control_phase, ControlPhase::Idle);
    assert_eq!(player.seed.transition.as_ref().unwrap().duration_byte, 8);
    for _ in 0..15 {
        player.step(1. / 60., &source).unwrap();
    }
    player.request_move(true).unwrap();
    for _ in 0..120 {
        player.step(1. / 60., &source).unwrap();
    }
    assert_eq!(player.control_phase, ControlPhase::Walking);
    player.request_move(false).unwrap();
    assert_eq!(player.control_phase, ControlPhase::StoppingA);
    assert_eq!(player.seed.transition.as_ref().unwrap().duration_byte, 10);
    for _ in 0..120 {
        player.step(1. / 60., &source).unwrap();
    }
    assert_eq!(player.control_phase, ControlPhase::Idle);
    for _ in 0..3 {
        player.request_move(true).unwrap();
        player.step(1. / 60., &source).unwrap();
        player.request_move(false).unwrap();
        player.step(1. / 60., &source).unwrap();
    }
    for _ in 0..120 {
        player.step(1. / 60., &source).unwrap();
    }
    assert_eq!(player.control_phase, ControlPhase::Idle);
    // Independent native re-entry events from both stop phases. This
    // compares request/target/duration, not captured full-pose timing.
    for (file, sample_index, stop, phase, target, action) in [
        (
            "stage43-tracking-sequence-20261009-153003.json",
            67,
            ControlPhase::StoppingA,
            0,
            ControlPhase::Slow,
            1,
        ),
        (
            "stage43-tracking-sequence-20261009-153143.json",
            89,
            ControlPhase::StoppingB,
            1,
            ControlPhase::Restart,
            51,
        ),
    ] {
        let raw: serde_json::Value = serde_json::from_slice(
            &std::fs::read(
                std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                    .join("../reports/jade")
                    .join(file),
            )
            .unwrap(),
        )
        .unwrap();
        let observed = &raw["samples"][sample_index];
        assert_eq!(observed["action_selection_unchanged"], true);
        assert_eq!(observed["current_action_index_a8"], action);
        player = load(&source).unwrap().unwrap();
        player.select(stop, false).unwrap();
        player.action_phase = phase;
        player.queued_action = Some(0);
        player.request_move(true).unwrap();
        assert_eq!(player.control_phase, stop);
        player.step(1. / 60., &source).unwrap();
        player.step(1. / 60., &source).unwrap();
        assert_eq!(player.control_phase, target);
        let queued = player.queued_action.map(|a| a as u64).unwrap_or(65535);
        assert_eq!(observed["requested_action_index_aa"], queued);
        let header = observed["transition_header_hex"].as_str().unwrap();
        assert_eq!(
            player.seed.transition.as_ref().unwrap().duration_byte,
            u8::from_str_radix(&header[0x59 * 2..0x5a * 2], 16).unwrap()
        );
        for _ in 0..30 {
            player.step(1. / 60., &source).unwrap();
        }
        assert_eq!(player.control_phase, ControlPhase::Walking);
    }
    player = load(&source).unwrap().unwrap();
    player.select(ControlPhase::Idle, false).unwrap();
    for _ in 0..200 {
        player.step(1. / 60., &source).unwrap();
        if player.control_phase == ControlPhase::WaitingIdle {
            break;
        }
    }
    assert_eq!(player.control_phase, ControlPhase::WaitingIdle);
    assert!(player.seed.transition.as_ref().unwrap().active);
    player.request_move(true).unwrap();
    assert_eq!(player.control_phase, ControlPhase::WaitingIdle);
    player.step(1. / 60., &source).unwrap();
    assert_eq!(player.control_phase, ControlPhase::WaitingIdle);
    for _ in 0..30 {
        player.step(1. / 60., &source).unwrap();
        if player.control_phase != ControlPhase::WaitingIdle {
            break;
        }
    }
    assert_eq!(player.control_phase, ControlPhase::Walking);
    let idle_press_raw: serde_json::Value = serde_json::from_slice(
        &std::fs::read(
            std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("../reports/jade/stage43-tracking-sequence-20261009-154821.json"),
        )
        .unwrap(),
    )
    .unwrap();
    let native = idle_press_raw["samples"]
        .as_array()
        .unwrap()
        .iter()
        .find(|s| {
            s["current_action_index_a8"] == 3
                && s["action_selection_unchanged"] == true
                && s["selector_inputs"]["unchanged"] == true
        })
        .unwrap();
    assert_eq!(native["requested_action_index_aa"], 65535);
    assert_eq!(player.queued_action, None);
    let h = native["transition_header_hex"].as_str().unwrap();
    assert_eq!(
        player.seed.transition.as_ref().unwrap().duration_byte,
        u8::from_str_radix(&h[0x59 * 2..0x5a * 2], 16).unwrap()
    );
}
