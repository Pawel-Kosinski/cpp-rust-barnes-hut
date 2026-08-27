#![allow(non_snake_case)]

use std::time::Instant;
use std::sync::OnceLock;
use std::fs::File;
use std::io::{self, BufRead};
use std::path::Path;

const TIME_STEP: f32 = 0.016;
const G : f32 = 1.0;
static THETA: OnceLock<f32> = OnceLock::new();

#[path = "../benchmark_options.rs"]
mod benchmark_options;

fn theta() -> f32 { *THETA.get().expect("benchmark options were not initialized") }

struct Particle {
    velocity_x: f32,
    velocity_y: f32,
    acc_x: f32,
    acc_y: f32,
    pos_x: f32,
    pos_y: f32,
    mass: f32,
    next_duplicate: usize,
}

struct NodePtr {
    bounds_x: f32,
    bounds_y: f32,
    half_size: f32,
    mass: f32,
    center_of_mass_x: f32,
    center_of_mass_y: f32,
    particle_index: usize,
    children: [Option<Box<NodePtr>>; 4],
}

impl Default for NodePtr {
    fn default() -> Self {
        NodePtr {
            bounds_x: 0.0,
            bounds_y: 0.0,
            half_size: 0.0,
            mass: 0.0,
            center_of_mass_x: 0.0,
            center_of_mass_y: 0.0,
            particle_index: usize::MAX,
            children: [None, None, None, None],
        }
    }
}

fn getQuadrant(node: &NodePtr, particle: &Particle) -> i32
{
    let mut quadrant = 0;
    if particle.pos_x > node.bounds_x { quadrant += 1; }
    if particle.pos_y > node.bounds_y { quadrant += 2; }
    quadrant
}

fn insertParticlePtr(node: &mut NodePtr, pIdx: usize, particles: &mut Vec<Particle>)
{
    if node.particle_index != usize::MAX
    {
        let oldIdx: usize = node.particle_index;
        if particles[pIdx].pos_x == particles[oldIdx].pos_x && particles[pIdx].pos_y == particles[oldIdx].pos_y
        {
            particles[pIdx].next_duplicate = oldIdx;
            node.particle_index = pIdx;
            return;
        }
    }

    if node.children[0].is_some()
    {
        let quad = getQuadrant(node, &particles[pIdx]) as usize;
        insertParticlePtr(node.children[quad].as_mut().unwrap(), pIdx, particles);
        return;
    }

    if node.particle_index == usize::MAX
    {
        node.particle_index = pIdx;
        return;
    }

    let oldPIdx = node.particle_index;
    node.particle_index = usize::MAX;
    let half_size = node.half_size / 2.0;
    for i in 0..4
    {
        let offset_x = ((i % 2) * 2) as f32 - 1.0;
        let offset_y = ((i / 2) * 2) as f32 - 1.0;

        node.children[i] = Some(Box::new(NodePtr {
            bounds_x: node.bounds_x + offset_x * half_size,
            bounds_y: node.bounds_y + offset_y * half_size,
            half_size,
            mass: 0.0,
            center_of_mass_x: 0.0,
            center_of_mass_y: 0.0,
            particle_index: usize::MAX,
            children: [None, None, None, None],
        }));
    }
    insertParticlePtr(node, oldPIdx, particles);
    insertParticlePtr(node, pIdx, particles);
}

fn computeMassDistributionPtr(node: &mut NodePtr, particles: &Vec<Particle>)
{
    if node.children[0].is_some()
    {
        node.mass = 0.0;
        node.center_of_mass_x = 0.0;
        node.center_of_mass_y = 0.0;

        for i in 0..4
        {
            computeMassDistributionPtr(node.children[i].as_mut().unwrap(), particles);
            let child = node.children[i].as_ref().unwrap();
            node.mass += child.mass;
            node.center_of_mass_x += child.center_of_mass_x * child.mass;
            node.center_of_mass_y += child.center_of_mass_y * child.mass;
        }
        if node.mass > 0.0
        {
            node.center_of_mass_x /= node.mass;
            node.center_of_mass_y /= node.mass;
        }
    }
    else if node.particle_index != usize::MAX
    {
        node.mass = 0.0;
        node.center_of_mass_x = 0.0;
        node.center_of_mass_y = 0.0;
        let mut source_idx = node.particle_index;
        while source_idx != usize::MAX {
            let source = &particles[source_idx];
            node.mass += source.mass;
            node.center_of_mass_x += source.pos_x * source.mass;
            node.center_of_mass_y += source.pos_y * source.mass;
            source_idx = source.next_duplicate;
        }
        if node.mass > 0.0 {
            node.center_of_mass_x /= node.mass;
            node.center_of_mass_y /= node.mass;
        }
    }

}

fn calculateForcesPtr(pIdx: usize, node: &NodePtr, particles: &[Particle]) -> (f32, f32)
{
    if node.mass <= 0.0 { return (0.0, 0.0); }

    let p = &particles[pIdx];
    if node.children[0].is_none() {
        let mut acc_x = 0.0;
        let mut acc_y = 0.0;
        let mut source_idx = node.particle_index;
        while source_idx != usize::MAX {
            if source_idx != pIdx {
                let source = &particles[source_idx];
                let dx = source.pos_x - p.pos_x;
                let dy = source.pos_y - p.pos_y;
                let dist_sq = dx * dx + dy * dy;
                if dist_sq >= 1e-5 {
                    let dist = dist_sq.sqrt();
                    let acc = G * source.mass / (dist_sq + 1.0);
                    acc_x += acc * (dx / dist);
                    acc_y += acc * (dy / dist);
                }
            }
            source_idx = particles[source_idx].next_duplicate;
        }
        return (acc_x, acc_y);
    }

    let dx = node.center_of_mass_x - p.pos_x;
    let dy = node.center_of_mass_y - p.pos_y;
    let dist_sq = dx * dx + dy * dy;
    let contains_target = (p.pos_x - node.bounds_x).abs() <= node.half_size
        && (p.pos_y - node.bounds_y).abs() <= node.half_size;

    let r_sq = 2.0 * node.half_size * node.half_size;

    if !contains_target && dist_sq >= 1e-5 && r_sq < theta() * theta() * dist_sq
    {
        let dist = dist_sq.sqrt();
        let acc = G * node.mass / (dist_sq + 1.0);
        (acc * (dx / dist), acc * (dy / dist))
    }
    else
    {
        let mut acc_x = 0.0;
        let mut acc_y = 0.0;
        for i in 0..4
        {
            let force = calculateForcesPtr(pIdx, node.children[i].as_ref().unwrap(), particles);
            acc_x += force.0;
            acc_y += force.1;
        }
        (acc_x, acc_y)
    }
}

#[allow(dead_code)]
fn countNodesPtr(node: &NodePtr) -> i32
{
    let mut count: i32 = 1;
    for i in 0..4
    {
        if node.children[i].is_some()
        {
            count += countNodesPtr(node.children[i].as_ref().unwrap());
        }
    }
    return count;
}

pub struct PhysicsMetrics {
    pub total_momentum_x: f64,
    pub total_momentum_y: f64,
    pub total_kinetic_energy: f64,
    pub center_x: f64,
    pub center_y: f64,
}

#[allow(dead_code)]
fn calculate_physics_diagnostics(particles: &[Particle]) -> PhysicsMetrics {
    let mut m = PhysicsMetrics {
        total_momentum_x: 0.0,
        total_momentum_y: 0.0,
        total_kinetic_energy: 0.0,
        center_x: 0.0,
        center_y: 0.0,
    };
    let mut total_mass = 0.0;

    for p in particles {
        // Casting to f64 reduces precision loss
        let mass = p.mass as f64;
        let vx = p.velocity_x as f64;
        let vy = p.velocity_y as f64;
        let px = p.pos_x as f64;
        let py = p.pos_y as f64;

        m.total_momentum_x += mass * vx;
        m.total_momentum_y += mass * vy;
        m.total_kinetic_energy += 0.5 * mass * (vx * vx + vy * vy);

        m.center_x += mass * px;
        m.center_y += mass * py;
        total_mass += mass;
    }

    m.center_x /= total_mass;
    m.center_y /= total_mass;

    m
}

#[allow(dead_code)]
fn validateForceAccuracy(current_frame: usize, bh_particles: &[Particle]) {
    println!("\n--- FORCE ACCURACY VALIDATION (Frame {}) ---", current_frame);

    let mut sum_diff_sq: f64 = 0.0;
    let mut sum_bf_sq: f64 = 0.0;
    let mut local_relative_errors = Vec::with_capacity(bh_particles.len());

    for i in 0..bh_particles.len() {
        let mut exact_acc_x: f32 = 0.0;
        let mut exact_acc_y: f32 = 0.0;

        for j in 0..bh_particles.len() {
            if i == j { continue; }
            let dx = bh_particles[j].pos_x - bh_particles[i].pos_x;
            let dy = bh_particles[j].pos_y - bh_particles[i].pos_y;
            let dist_sq = dx * dx + dy * dy;

            if dist_sq < 1e-5 { continue; }

            let dist = dist_sq.sqrt();
            let acc = G * bh_particles[j].mass / (dist_sq + 1.0);
            exact_acc_x += acc * (dx / dist);
            exact_acc_y += acc * (dy / dist);
        }

        let diff_x = (bh_particles[i].acc_x - exact_acc_x) as f64;
        let diff_y = (bh_particles[i].acc_y - exact_acc_y) as f64;

        let diff_sq = diff_x * diff_x + diff_y * diff_y;
        let bf_sq = (exact_acc_x * exact_acc_x + exact_acc_y * exact_acc_y) as f64;

        sum_diff_sq += diff_sq;
        sum_bf_sq += bf_sq;

        let exact_norm = bf_sq.sqrt();
        let diff_norm = diff_sq.sqrt();

        if exact_norm > 1e-6 {
            local_relative_errors.push(diff_norm / exact_norm);
        }
    }

    let rms_error = (sum_diff_sq / sum_bf_sq).sqrt();

    local_relative_errors.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let mut p95_error = 0.0;
    if !local_relative_errors.is_empty() {
        let p95_index = (0.95 * local_relative_errors.len() as f64) as usize;
        p95_error = local_relative_errors[p95_index];
    }

    println!("Global force error (RMS): {:.4} %", rms_error * 100.0);
    println!("95th percentile error:      {:.4} %", p95_error * 100.0);
    println!("--------------------------------------------------");
}

fn mainMain(options: &benchmark_options::BenchmarkOptions)
{
    let mut particles = Vec::new();

    let path = Path::new(&options.input);
    let file = match File::open(&path) {
        Ok(f) => f,
        Err(_) => {
            eprintln!("Error: Could not open input file {}.", options.input);
            std::process::exit(1);
        }
    };

    let reader = io::BufReader::new(file);

    for line in reader.lines() {
        let line = line.expect("Error while reading a line from the file");

        // Split the line by spaces
        let parts: Vec<&str> = line.split_whitespace().collect();

        if parts.len() == 5 {
            particles.push(Particle {
                pos_x: parts[0].parse().unwrap(),
                pos_y: parts[1].parse().unwrap(),
                velocity_x: parts[2].parse().unwrap(),
                velocity_y: parts[3].parse().unwrap(),
                mass: parts[4].parse().unwrap(),
                acc_x: 0.0,
                acc_y: 0.0,
                next_duplicate: usize::MAX,
            });
        }
    }

    let mut total_force_time_ms = 0.0;
    let mut total_tree_time_ms = 0.0;
    let mut total_cleanup_time_ms = 0.0;
    if let Err(message) = benchmark_options::validate_particle_count(options, particles.len()) {
        eprintln!("{message}");
        return;
    }

    for frame in 0..options.total_frames() {

        let mut start_time = Instant::now();

        let mut minX = particles[0].pos_x;
        let mut maxX = particles[0].pos_x;
        let mut minY = particles[0].pos_y;
        let mut maxY = particles[0].pos_y;

        for p in &particles
        {
            if p.pos_x < minX { minX = p.pos_x; }
            if p.pos_x > maxX { maxX = p.pos_x; }
            if p.pos_y < minY { minY = p.pos_y; }
            if p.pos_y > maxY { maxY = p.pos_y; }
        }

        let centerX = (minX + maxX) / 2.0;
        let centerY = (minY + maxY) / 2.0;
        let halfWidth = (maxX - minX) / 2.0;
        let halfHeight = (maxY - minY) / 2.0;
        let maxHalfSize = f32::max(halfWidth, halfHeight) + 1.0;

        let mut root: NodePtr = NodePtr::default();
        root.bounds_x = centerX;
        root.bounds_y = centerY;
        root.half_size = maxHalfSize;

        for particle in &mut particles { particle.next_duplicate = usize::MAX; }
        for j in 0..particles.len()
        {
            insertParticlePtr(&mut root, j, &mut particles);
        }
        // if i == 0 {
        //     let particlesMem: usize = particles.capacity() * std::mem::size_of::<Particle>();
        //     let nodeCount = countNodesPtr(&root);
        //     let treeMem = (nodeCount as usize) * std::mem::size_of::<NodePtr>();
        //     let totalAppMemMB = (particlesMem + treeMem) as f64 / (1024.0 * 1024.0);

        //     println!("Algorithm memory usage: {} MB", totalAppMemMB);
        //     println!("Created {} tree nodes", nodeCount);
        //     println!("Size of Particle: {:.6} bytes", std::mem::size_of::<Particle>());
        //     println!("Size of NodePtr (V2): {:.6} bytes", std::mem::size_of::<NodePtr>());
        // }

        computeMassDistributionPtr(&mut root, &particles);
        let tree_time_ms = start_time.elapsed().as_secs_f64() * 1000.0;
        if frame >= options.warmup_frames {
            total_tree_time_ms += tree_time_ms;
        }

        start_time = Instant::now();
        for k in 0..particles.len()
        {
            let force = calculateForcesPtr(k, &root, &particles);
            particles[k].acc_x += force.0;
            particles[k].acc_y += force.1;
        }

        if frame == options.warmup_frames {
            if let Some(path) = options.dump_forces.as_deref() {
                if let Err(message) = benchmark_options::write_forces(
                    path,
                    particles.iter().map(|particle| (particle.acc_x, particle.acc_y)),
                ) {
                    eprintln!("{message}");
                    return;
                }
            }
        }


        // if i == FRAMES - 1 || i == 0 || i == 150{
        //     validateForceAccuracy(i, &particles);
        // }

        for p in &mut particles
        {
            p.velocity_x += p.acc_x * TIME_STEP;
            p.velocity_y += p.acc_y * TIME_STEP;
            p.pos_x += p.velocity_x * TIME_STEP;
            p.pos_y += p.velocity_y * TIME_STEP;
            p.acc_x = 0.0;
            p.acc_y = 0.0;
        }
        let force_time_ms = start_time.elapsed().as_secs_f64() * 1000.0;
        if frame >= options.warmup_frames {
            total_force_time_ms += force_time_ms;
        }

        let cleanup_start = Instant::now();
        drop(root);
        let cleanup_time_ms = cleanup_start.elapsed().as_secs_f64() * 1000.0;
        if frame >= options.warmup_frames {
            total_cleanup_time_ms += cleanup_time_ms;
        }


}

    println!("Tree construction time: {:.4} ms / frame", total_tree_time_ms / (options.frames as f64));
    println!("Force/update time: {:.4} ms / frame", total_force_time_ms / (options.frames as f64));
    println!("Cleanup time: {:.4} ms / frame", total_cleanup_time_ms / (options.frames as f64));
    println!("Total measured time: {:.4} ms", total_force_time_ms + total_tree_time_ms + total_cleanup_time_ms);

    // let ref_path = Path::new("reference_1000k.txt");
    // match File::open(&ref_path) {
    //     Ok(ref_file) => {
    //         let ref_reader = io::BufReader::new(ref_file);
    //         let mut total_error = 0.0f32;
    //         let mut particle_count = 0usize;
    //         let mut current_error = 0.0f32;
    //         let mut max_error = 0.0f32;

    //         for (idx, line) in ref_reader.lines().enumerate() {
    //             if idx >= NUM_PARTICLES {
    //                 break;
    //             }

    //             let line = match line {
    //                 Ok(l) => l,
    //                 Err(_) => break,
    //             };

    //             let parts: Vec<&str> = line.split_whitespace().collect();
    //             if parts.len() >= 2 {
    //                 let ref_x: f32 = match parts[0].parse() {
    //                     Ok(x) => x,
    //                     Err(_) => break,
    //                 };
    //                 let ref_y: f32 = match parts[1].parse() {
    //                     Ok(y) => y,
    //                     Err(_) => break,
    //                 };

    //                 let dx = particles[idx].pos_x - ref_x;
    //                 let dy = particles[idx].pos_y - ref_y;
    //                 current_error = (dx * dx + dy * dy).sqrt();
    //                 total_error += current_error;
    //                 if current_error > max_error {
    //                     max_error = current_error;
    //                 }
    //                 particle_count += 1;
    //             }
    //         }

    //         if particle_count > 0 {
    //             let mean_absolute_error = total_error / particle_count as f32;
    //             println!("Mean absolute position error (MAE): {:.6} units", mean_absolute_error);
    //             println!("Maximum position error: {:.6} units", max_error);
    //         }
    //     }
    //     Err(_) => {
    //         eprintln!("file error.");
    //     }
    // }
}

fn main()
{
    let options = match benchmark_options::parse_options() {
        Ok(options) => options,
        Err(message) => { eprintln!("{message}"); std::process::exit(1); }
    };
    THETA.set(options.theta).expect("benchmark options initialized once");
    mainMain(&options);
}
