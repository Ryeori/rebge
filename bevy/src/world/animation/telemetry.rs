//! Opt-in diagnostic movement recording.
use super::*;

/// Opt-in measurement only. Actor matrices retain source coordinates; mesh
/// vertices use Bevy coordinates and must never be mixed in a velocity dot product.
#[derive(Default)]
pub(crate) struct MovementTrace {
    initialized: bool,
    file: Option<std::io::BufWriter<std::fs::File>>,
    frame: u64,
}
impl MovementTrace {
    pub(super) fn record(&mut self, player: &Player, delta: f32, vertices: &[(usize, Vec<[f32; 3]>)]) {
        use std::io::Write;
        if !self.initialized {
            self.initialized = true;
            if let Some(path) = std::env::var_os("REBGE_MOVEMENT_TRACE") {
                let path = std::path::PathBuf::from(path);
                let allowed = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                    .join("../reports").canonicalize();
                let parent = path.parent().and_then(|p| p.canonicalize().ok());
                if let (Ok(allowed), Some(parent)) = (allowed, parent)
                    && parent.starts_with(allowed) {
                    match std::fs::File::create(&path) {
                        Ok(file) => self.file = Some(std::io::BufWriter::new(file)),
                        Err(e) => error!("Cannot create movement trace: {e}"),
                    }
                } else {
                    error!("Movement trace must be inside project reports/");
                }
            }
        }
        let Some(file) = &mut self.file else { return };
        self.frame += 1;
        let actor = player.pose.nodes[&player.seed.actor_address].world;
        let blend = player.seed.transition.as_ref().map(|t| serde_json::json!({
            "active": t.active, "duration_byte":t.duration_byte, "ratio":t.ratio,
            "terminal_pose":t.interrupted_pose.is_some()}));
        let roots: Vec<_> = player.pose.bone_addresses.iter().take(1).map(|address|
            player.pose.nodes[address].local.map(|v|v.0)).collect();
        let mut centroid = [0f64;3];
        let mut count = 0usize;
        for (_, positions) in vertices {
            for v in positions { for k in 0..3 { centroid[k] += v[k] as f64; } count += 1; }
        }
        if count > 0 { for v in &mut centroid { *v /= count as f64; } }
        let row = serde_json::json!({"schema":"rebge-movement-frame-v1",
            "unix_ns":std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default().as_nanos() as u64,
            "frame":self.frame,"delta":delta,"scene_time":player.scene_time,
            "phase":format!("{:?}",player.control_phase),"action_phase":player.action_phase,
            "speed_byte":player.seed.speed,"input_strength":player.input_strength,
            "run_requested":player.run_requested,"move_requested":player.move_requested,
            "approximate_turn_speed":player.selection_velocity.length(),
            "approximate_turn_velocity":player.selection_velocity.to_array(),
            "last_qualified_turn_speed_proxy":player.last_turn_candidate_speed,
            "pending_moving_turn":player.pending_moving_turn,
            "pending_standing_turn":player.pending_standing_turn.map(|phase|format!("{phase:?}")),
            "direction":player.control_direction.to_array(),"actor_source_matrix":actor,
            "root_local":roots,"mesh_centroid_bevy":centroid,"blend":blend});
        if let Err(e) = serde_json::to_writer(&mut *file, &row)
            .and_then(|_| file.write_all(b"\n").map_err(serde_json::Error::io))
            .and_then(|_| file.flush().map_err(serde_json::Error::io)) {
            error!("Movement trace failed: {e}");
            self.file = None;
        }
    }
}

