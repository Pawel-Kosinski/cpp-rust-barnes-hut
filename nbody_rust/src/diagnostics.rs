use std::fs::File;
use std::io::{BufWriter, Write};

pub struct DiagnosticWriter {
    output: Option<BufWriter<File>>,
    dt: f64,
    stride: usize,
}

impl DiagnosticWriter {
    pub fn new(path: Option<&str>, dt: f32, stride: usize) -> Self {
        let output = path.map(|p| {
            let mut out = BufWriter::new(File::create(p).expect("Cannot open diagnostics"));
            writeln!(out, "step,time,momentum_x,momentum_y,angular_momentum,kinetic,potential,total_energy").expect("Write diagnostics header");
            out
        });
        Self { output, dt: dt as f64, stride }
    }

    pub fn record<I>(&mut self, step: usize, states: I, final_step: bool)
    where I: IntoIterator<Item = [f32; 5]> {
        if self.output.is_none() || (!final_step && step % self.stride != 0) { return; }
        let particles: Vec<[f64; 5]> = states.into_iter().map(|p| p.map(|v| v as f64)).collect();
        let (mut px, mut py, mut angular, mut kinetic, mut potential) = (0.0, 0.0, 0.0, 0.0, 0.0);
        for (i, p) in particles.iter().enumerate() {
            let [x, y, vx, vy, mass] = *p;
            px += mass * vx;
            py += mass * vy;
            angular += mass * (x * vy - y * vx);
            kinetic += 0.5 * mass * (vx * vx + vy * vy);
            // Potential consistent with the actual cutoff and force law.
            for q in &particles[..i] {
                let r = ((x - q[0]).powi(2) + (y - q[1]).powi(2)).max(1e-5).sqrt();
                potential -= mass * q[4] * 1.0_f64.atan2(r);
            }
        }
        let out = self.output.as_mut().unwrap();
        writeln!(out, "{step},{:.17},{px:.17},{py:.17},{angular:.17},{kinetic:.17},{potential:.17},{:.17}", step as f64 * self.dt, kinetic + potential).expect("Write diagnostics");
        out.flush().expect("Flush diagnostics");
    }
}

pub fn write_state<I>(path: Option<&str>, states: I)
where I: IntoIterator<Item = [f32; 5]> {
    if let Some(path) = path {
        let mut out = BufWriter::new(File::create(path).expect("Cannot open state snapshot"));
        for [x, y, vx, vy, mass] in states {
            writeln!(out, "{x:.9} {y:.9} {vx:.9} {vy:.9} {mass:.9}").expect("Write state snapshot");
        }
        out.flush().expect("Flush state snapshot");
    }
}

pub fn write_memory_report(path: Option<&str>, nodes: usize, node_bytes: usize,
    tree_capacity: usize, tree_heap_blocks: usize, particle_bytes: usize, force_buffer_bytes: usize) {
    if let Some(path) = path {
        let mut out = BufWriter::new(File::create(path).expect("Cannot open memory report"));
        writeln!(out, "tree_nodes,node_bytes,tree_capacity,tree_heap_blocks,tree_reserved_bytes,particle_reserved_bytes,force_buffer_bytes,structural_bytes").expect("Write memory header");
        writeln!(out, "{nodes},{node_bytes},{tree_capacity},{tree_heap_blocks},{},{particle_bytes},{force_buffer_bytes},{}", tree_capacity * node_bytes, tree_capacity * node_bytes + particle_bytes + force_buffer_bytes).expect("Write memory report");
        out.flush().expect("Flush memory report");
    }
}
