#![allow(non_snake_case)]

use std::time::Instant;
use std::sync::OnceLock;
use std::fs::File;
use std::io::{self, BufRead};
use std::path::Path;
use rayon::{ThreadPoolBuilder, prelude::*};

const TIME_STEP: f32 = 0.016;
const G : f32 = 1.0;
static THETA: OnceLock<f32> = OnceLock::new();

#[path = "../benchmark_options.rs"]
mod benchmark_options;

fn theta() -> f32 { *THETA.get().expect("benchmark options were not initialized") }

#[derive(Clone)]
struct Particle {
    velocity_x: f32,
    velocity_y: f32,
    acc_x: f32,
    acc_y: f32,
    pos_x: f32,
    pos_y: f32,
    mass: f32,
}

struct Node {
    bounds_x: f32,
    bounds_y: f32,
    half_size: f32,
    mass: f32,
    center_of_mass_x: f32,
    center_of_mass_y: f32,
    particle_index: usize,
    children: [usize; 4],
    next: usize,
}

impl Default for Node {
    fn default() -> Self {
        Node {
            bounds_x: 0.0,
            bounds_y: 0.0,
            half_size: 0.0,
            mass: 0.0,
            center_of_mass_x: 0.0,
            center_of_mass_y: 0.0,
            particle_index: usize::MAX,
            children: [usize::MAX, usize::MAX, usize::MAX, usize::MAX],
            next: usize::MAX,
        }
    }
}

fn getQuadrant(node: &Node, particle: &Particle) -> i32
{
    let mut quadrant = 0;
    if particle.pos_x > node.bounds_x { quadrant += 1; }
    if particle.pos_y > node.bounds_y { quadrant += 2; }
    quadrant
}

fn threadTree(nodeIdx: usize, nextIdx: usize, arena: &mut Vec<Node>)
{
    arena[nodeIdx].next = nextIdx;
    if arena[nodeIdx].children[0] != usize::MAX
    {
        for i in 0..3
        {
            threadTree(arena[nodeIdx].children[i], arena[nodeIdx].children[i + 1], arena);
        }
        threadTree(arena[nodeIdx].children[3], nextIdx, arena);
    }
}

fn insertParticle(nodeIdx: usize, pIdx: usize, arena: &mut Vec<Node>,  particles: &mut Vec<Particle>)
{
    if arena[nodeIdx].particle_index != usize::MAX
    {
        let oldIdx: usize = arena[nodeIdx].particle_index;
        let mut shift = 0.0001;
        while particles[pIdx].pos_x == particles[oldIdx].pos_x && particles[pIdx].pos_y == particles[oldIdx].pos_y
        {
            particles[pIdx].pos_x += shift;
            shift *= 2.0;
        }
    }

    if arena[nodeIdx].particle_index == usize::MAX && arena[nodeIdx].children[0] == usize::MAX
    {
        arena[nodeIdx].particle_index = pIdx;
        return;
    }

    if arena[nodeIdx].children[0] != usize::MAX
    {
        let quad = getQuadrant(&arena[nodeIdx], &particles[pIdx]) as usize;
        insertParticle( arena[nodeIdx].children[quad], pIdx, arena, particles);
        return;
    }

    let oldPIdx = arena[nodeIdx].particle_index;
    arena[nodeIdx].particle_index = usize::MAX;
    let half_size = arena[nodeIdx].half_size / 2.0;

    for i in 0..4
    {
        let offset_x = ((i % 2) * 2) as f32 - 1.0;
        let offset_y = ((i / 2) * 2) as f32 - 1.0;

        let child_idx = arena.len();
        arena[nodeIdx].children[i] = child_idx;

        arena.push(Node {
            bounds_x: arena[nodeIdx].bounds_x + offset_x * half_size,
            bounds_y: arena[nodeIdx].bounds_y + offset_y * half_size,
            half_size,
            mass: 0.0,
            center_of_mass_x: 0.0,
            center_of_mass_y: 0.0,
            particle_index: usize::MAX,
            children: [usize::MAX, usize::MAX, usize::MAX, usize::MAX],
            next: usize::MAX,
        });
    }
    insertParticle(nodeIdx, oldPIdx, arena, particles);
    insertParticle(nodeIdx, pIdx, arena, particles);
}

fn computeMassDistribution(nodeIdx: usize, arena: &mut Vec<Node>, particles: &Vec<Particle>)
{
    if arena[nodeIdx].children[0] != usize::MAX
    {
        arena[nodeIdx].mass = 0.0;
        arena[nodeIdx].center_of_mass_x = 0.0;
        arena[nodeIdx].center_of_mass_y = 0.0;

        for i in 0..4
        {
            let childIdx = arena[nodeIdx].children[i];
            computeMassDistribution(childIdx, arena, particles);

            arena[nodeIdx].mass += arena[childIdx].mass;
            arena[nodeIdx].center_of_mass_x += arena[childIdx].center_of_mass_x * arena[childIdx].mass;
            arena[nodeIdx].center_of_mass_y += arena[childIdx].center_of_mass_y * arena[childIdx].mass;
        }
        if arena[nodeIdx].mass > 0.0
        {
            arena[nodeIdx].center_of_mass_x /= arena[nodeIdx].mass;
            arena[nodeIdx].center_of_mass_y /= arena[nodeIdx].mass;
        }
    }
    else if arena[nodeIdx].particle_index != usize::MAX
    {
        let pIdx = arena[nodeIdx].particle_index;
        arena[nodeIdx].mass = particles[pIdx].mass;
        arena[nodeIdx].center_of_mass_x = particles[pIdx].pos_x;
        arena[nodeIdx].center_of_mass_y = particles[pIdx].pos_y;
    }
    else
    {
        arena[nodeIdx].mass = 0.0;
        arena[nodeIdx].center_of_mass_x = 0.0;
        arena[nodeIdx].center_of_mass_y = 0.0;
    }
}

// The signature was changed to avoid modifying the vector directly inside the function.
// Teraz funkcja tylko oblicza i ZWRACA nowe przyspieszenie.
fn calculateForces(pIdx: usize, startNodeIdx: usize, arena: &[Node], particles: &[Particle]) -> (f32, f32)
{
    if startNodeIdx == usize::MAX { return (0.0, 0.0); }

    let mut acc_x = 0.0;
    let mut acc_y = 0.0;

    let mut currNodeIdx: usize = startNodeIdx;
    while currNodeIdx != usize::MAX
    {
        let node = &arena[currNodeIdx];
        let dx = node.center_of_mass_x - particles[pIdx].pos_x;
        let dy = node.center_of_mass_y - particles[pIdx].pos_y;
        let dist_sq = dx * dx + dy * dy;

        if dist_sq < 1e-5 {
            currNodeIdx = node.next;
            continue;
        }

        let r_sq = 2.0 * node.half_size * node.half_size;
        if r_sq < theta() * theta() * dist_sq || node.children[0] == usize::MAX
        {
            let dist = dist_sq.sqrt();
            let acc = G * node.mass / (dist_sq + 1.0);
            acc_x += acc * (dx / dist);
            acc_y += acc * (dy / dist);
            currNodeIdx = node.next;
        }
        else
        {
            currNodeIdx = node.children[0];
        }
    }

    (acc_x, acc_y)
}

//  pub struct PhysicsMetrics {
//     pub total_momentum_x: f64,
//     pub total_momentum_y: f64,
//     pub total_kinetic_energy: f64,
//     pub center_x: f64,
//     pub center_y: f64,
// }

// pub fn calculate_physics_diagnostics(particles: &[Particle]) -> PhysicsMetrics {
//     let mut m = PhysicsMetrics {
//         total_momentum_x: 0.0,
//         total_momentum_y: 0.0,
//         total_kinetic_energy: 0.0,
//         center_x: 0.0,
//         center_y: 0.0,
//     };
//     let mut total_mass = 0.0;

//     for p in particles {
//         // Casting to f64 reduces precision loss
//         let mass = p.mass as f64;
//         let vx = p.velocity_x as f64;
//         let vy = p.velocity_y as f64;
//         let px = p.pos_x as f64;
//         let py = p.pos_y as f64;

//         m.total_momentum_x += mass * vx;
//         m.total_momentum_y += mass * vy;
//         m.total_kinetic_energy += 0.5 * mass * (vx * vx + vy * vy);

//         m.center_x += mass * px;
//         m.center_y += mass * py;
//         total_mass += mass;
//     }

//     m.center_x /= total_mass;
//     m.center_y /= total_mass;

//     m
// }

#[allow(dead_code)]
fn validateForceAccuracyParallel(current_frame: usize, bh_particles: &[Particle], bh_forces: &[(f32, f32)]) {
    println!("\n--- FORCE ACCURACY VALIDATION (Frame {}) ---", current_frame);

    let results: Vec<(f64, f64, Option<f64>)> = bh_particles.par_iter().enumerate().map(|(i, _)| {
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

        let bh_acc_x = bh_forces[i].0 as f64;
        let bh_acc_y = bh_forces[i].1 as f64;

        let diff_x = bh_acc_x - exact_acc_x as f64;
        let diff_y = bh_acc_y - exact_acc_y as f64;

        let diff_sq = diff_x * diff_x + diff_y * diff_y;
        let bf_sq = (exact_acc_x * exact_acc_x + exact_acc_y * exact_acc_y) as f64;

        let exact_norm = bf_sq.sqrt();
        let diff_norm = diff_sq.sqrt();

        let rel_err = if exact_norm > 1e-6 {
            Some(diff_norm / exact_norm)
        } else {
            None
        };

        (diff_sq, bf_sq, rel_err)
    }).collect();

    let mut sum_diff_sq: f64 = 0.0;
    let mut sum_bf_sq: f64 = 0.0;
    let mut local_relative_errors = Vec::with_capacity(bh_particles.len());

    for (diff_sq, bf_sq, rel_err) in results {
        sum_diff_sq += diff_sq;
        sum_bf_sq += bf_sq;
        if let Some(err) = rel_err {
            local_relative_errors.push(err);
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
    //let mut arena: Vec<Node> = Vec::with_capacity(3 * NUM_PARTICLES);
    let mut arena: Vec<Node> = Vec::new();

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
            });
        }
    }

    let mut total_force_time_ms = 0.0;
    let mut total_tree_time_ms = 0.0;
    // Reuse the output buffer so allocation is not charged to each force phase.
    let mut forces = vec![(0.0f32, 0.0f32); particles.len()];
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

        let mut root: Node = Node::default();
        root.bounds_x = centerX;
        root.bounds_y = centerY;
        root.half_size = maxHalfSize;
        arena.clear();
        arena.push(root);

        for i in 0..particles.len()
        {
            insertParticle(0, i, &mut arena, &mut particles);
        }
        // if j == 0 {
        //     let particlesMem: usize = particles.capacity() * std::mem::size_of::<Particle>();
        //     let arenaMem: usize = arena.capacity() * std::mem::size_of::<Node>();
        //     let totalAppMemMB = (particlesMem + arenaMem) as f64 / (1024.0 * 1024.0);
        //     println!("Algorithm memory usage: {:.6} MB", totalAppMemMB);
        //     println!("Created {} tree nodes", arena.len());
        //     println!("Size of Particle: {:.6} bytes", std::mem::size_of::<Particle>());
        //     println!("Size of Node (V4/V5): {:.6} bytes", std::mem::size_of::<Node>());
        // }

        computeMassDistribution(0, &mut arena, &particles);
        threadTree(0, usize::MAX, &mut arena);

        let tree_time_ms = start_time.elapsed().as_secs_f64() * 1000.0;
        if frame >= options.warmup_frames {
            total_tree_time_ms += tree_time_ms;
        }

        //  if j == 0 {
        //     println!("Tree construction time frame 0: {:.4} ms", total_tree_time_ms);
        //     println!("Tree construction cycles frame 0: {} cycles", total_cycles_tree);
        // }

        start_time = Instant::now();

        // The `par_iter_mut()` iterator splits the particle vector across CPU cores
        //particles.par_iter_mut().enumerate().for_each(|(i, p)| {});

        //Compute forces in parallel and collect them into a new vector
        forces.par_iter_mut().enumerate().for_each(|(i, force)| {
            *force = calculateForces(i, 0, &arena, &particles);
        });

        if frame == options.warmup_frames {
            if let Some(path) = options.dump_forces.as_deref() {
                if let Err(message) = benchmark_options::write_forces(path, forces.iter().copied()) {
                    eprintln!("{message}");
                    return;
                }
            }
        }

        // if j == FRAMES - 1 || j == 0 || j == 150{
        //     validateForceAccuracyParallel(j, &particles, &forces);
        // }

        //Apply forces in parallel to the original particles
        particles.par_iter_mut().zip(forces.par_iter()).for_each(|(p, (acc_x, acc_y))| {
            p.velocity_x += acc_x * TIME_STEP;
            p.velocity_y += acc_y * TIME_STEP;
            p.pos_x += p.velocity_x * TIME_STEP;
            p.pos_y += p.velocity_y * TIME_STEP;
            p.acc_x = 0.0;
            p.acc_y = 0.0;
        });

        let force_time_ms = start_time.elapsed().as_secs_f64() * 1000.0;
        if frame >= options.warmup_frames {
            total_force_time_ms += force_time_ms;
        }

        // if j % 25 == 0 || j == FRAMES - 1 {
        //     let metrics = calculate_physics_diagnostics(&particles);
        //     println!("Frame {}:", j);
        //     println!("Ped ({:.6}, {:.6})", metrics.total_momentum_x, metrics.total_momentum_y);
        //     println!("Energia kinetyczna {:.6}", metrics.total_kinetic_energy);
        //     println!("Srodek masy ({:.6}, {:.6})", metrics.center_x, metrics.center_y);
        // }
    }

    println!("Tree construction time: {:.4} ms / frame", total_tree_time_ms / (options.frames as f64));
    println!("Force/update time: {:.4} ms / frame", total_force_time_ms / (options.frames as f64));
    println!("Cleanup time: 0.0000 ms / frame");
    println!("Total measured time: {:.4} ms", total_force_time_ms + total_tree_time_ms);

    // let ref_path = Path::new("reference_1000k.txt");
    // match File::open(&ref_path) {
    //     Ok(ref_file) => {
    //         let ref_reader = io::BufReader::new(ref_file);
    //         let mut total_error = 0.0f32;
    //         let mut particle_count = 0usize;
    //         let mut current_error = 0.0f32;
    //         let mut max_error = 0.0f32;

    //         for (idx, line) in ref_reader.lines().enumerate() {
    //             if idx >= NUM_PARTICLES { break; }
    //             let line = match line { Ok(l) => l, Err(_) => break, };
    //             let parts: Vec<&str> = line.split_whitespace().collect();
    //             if parts.len() >= 2 {
    //                 let ref_x: f32 = match parts[0].parse() { Ok(x) => x, Err(_) => break, };
    //                 let ref_y: f32 = match parts[1].parse() { Ok(y) => y, Err(_) => break, };

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
    //     Err(_) => { eprintln!("file error."); }
    // }
}

fn main() {
    let options = match benchmark_options::parse_options() {
        Ok(options) => options,
        Err(message) => { eprintln!("{message}"); std::process::exit(1); }
    };
    THETA.set(options.theta).expect("benchmark options initialized once");
    let mut pool = ThreadPoolBuilder::new();
    if options.threads > 0 { pool = pool.num_threads(options.threads); }
    pool.build_global().expect("Rayon thread pool initialized once");
    mainMain(&options);
}
