use std::time::Instant;
use std::fs::File;
use std::io::{self, BufRead, Write};
use std::path::Path;

const TIME_STEP: f32 = 0.016;
const G : f32 = 1.0;

#[path = "../benchmark_options.rs"]
mod benchmark_options;

struct Particle {
    velocity_x: f32,
    velocity_y: f32,
    acc_x: f32,
    acc_y: f32,
    pos_x: f32,
    pos_y: f32,
    mass: f32,
}

pub struct PhysicsMetrics {
    pub total_momentum_x: f64,
    pub total_momentum_y: f64,
    pub total_kinetic_energy: f64,
    pub center_x: f64,
    pub center_y: f64,
}

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

fn main() {
    let options = match benchmark_options::parse_options() {
        Ok(options) => options,
        Err(message) => { eprintln!("{message}"); std::process::exit(1); }
    };
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
            });
        }
    }
    if let Err(message) = benchmark_options::validate_particle_count(&options, particles.len()) {
        eprintln!("{message}");
        std::process::exit(1);
    }

    let mut total_force_time_ms = 0.0;

    for j in 0..options.frames {

        let start_time = Instant::now();

        for i in 0..particles.len() {
            let mut acc_x: f32 = 0.0;
            let mut acc_y: f32 = 0.0;
            let particle_a_pos_x = particles[i].pos_x;
            let particle_a_pos_y = particles[i].pos_y;

            for j in 0..particles.len() {
                if i == j {
                    continue;
                }
                let particle_b = &particles[j];
                let dx = particle_b.pos_x - particle_a_pos_x;
                let dy = particle_b.pos_y - particle_a_pos_y;
                let dist_sq = dx * dx + dy * dy;

                let distance = dist_sq.sqrt();

                let acc = G * particle_b.mass / (dist_sq + 1.0);

                acc_x += acc * (dx / distance);
                acc_y += acc * (dy / distance);
            }
            particles[i].acc_x = acc_x;
            particles[i].acc_y = acc_y;
        }

        let end_time = start_time.elapsed();

        if j == 0 {
            let particles_mem: usize = particles.capacity() * std::mem::size_of::<Particle>();
            let total_app_mem_mb = (particles_mem) as f64 / (1024.0 * 1024.0);
            println!("Algorithm memory usage: {} MB", total_app_mem_mb);
            println!("Size of Particle: {:.6} bytes", std::mem::size_of::<Particle>());
        }

        // Euler integration (position update)
        for i in 0..particles.len() {
            particles[i].velocity_x += particles[i].acc_x * TIME_STEP;
            particles[i].velocity_y += particles[i].acc_y * TIME_STEP;
            particles[i].pos_x += particles[i].velocity_x * TIME_STEP;
            particles[i].pos_y += particles[i].velocity_y * TIME_STEP;

            particles[i].acc_x = 0.0;
            particles[i].acc_y = 0.0;
        }
        total_force_time_ms += end_time.as_secs_f64() * 1000.0;

        if j == 0 || j == options.frames - 1 {
            let metrics = calculate_physics_diagnostics(&particles);
            println!("Frame {}:", j);
            println!("Ped ({:.6}, {:.6})", metrics.total_momentum_x, metrics.total_momentum_y);
            println!("Energia kinetyczna {:.6}", metrics.total_kinetic_energy);
            println!("Srodek masy ({:.6}, {:.6})", metrics.center_x, metrics.center_y);
        }
    }

    let out_file = std::fs::File::create("reference_50k.txt").unwrap();
    let mut writer = std::io::BufWriter::new(out_file);
    for p in &particles {
        writeln!(writer, "{:.6} {:.6}", p.pos_x, p.pos_y).unwrap();
    }

    println!("Force calculation time: {:.4} ms / frame", total_force_time_ms / (options.frames as f64));
    println!("Total simulation time: {:.4} ms", total_force_time_ms);
}
