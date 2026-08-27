use std::time::Instant;
use std::fs::File;
use std::io::{self, BufRead};
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

    for frame in 0..options.total_frames() {

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
                if dist_sq < 1e-5 {
                    continue;
                }

                let distance = dist_sq.sqrt();

                let acc = G * particle_b.mass / (dist_sq + 1.0);

                acc_x += acc * (dx / distance);
                acc_y += acc * (dy / distance);
            }
            particles[i].acc_x = acc_x;
            particles[i].acc_y = acc_y;
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

        // Euler integration (position update)
        for i in 0..particles.len() {
            particles[i].velocity_x += particles[i].acc_x * TIME_STEP;
            particles[i].velocity_y += particles[i].acc_y * TIME_STEP;
            particles[i].pos_x += particles[i].velocity_x * TIME_STEP;
            particles[i].pos_y += particles[i].velocity_y * TIME_STEP;

            particles[i].acc_x = 0.0;
            particles[i].acc_y = 0.0;
        }
        let force_time_ms = start_time.elapsed().as_secs_f64() * 1000.0;
        if frame >= options.warmup_frames {
            total_force_time_ms += force_time_ms;
        }

        if frame == options.warmup_frames || frame == options.total_frames() - 1 {
            let metrics = calculate_physics_diagnostics(&particles);
            println!("Frame {}:", frame);
            println!("Momentum ({:.6}, {:.6})", metrics.total_momentum_x, metrics.total_momentum_y);
            println!("Kinetic energy {:.6}", metrics.total_kinetic_energy);
            println!("Center of mass ({:.6}, {:.6})", metrics.center_x, metrics.center_y);
        }
    }

    println!("Tree construction time: 0.0000 ms / frame");
    println!("Force/update time: {:.4} ms / frame", total_force_time_ms / (options.frames as f64));
    println!("Cleanup time: 0.0000 ms / frame");
    println!("Total measured time: {:.4} ms", total_force_time_ms);
}
