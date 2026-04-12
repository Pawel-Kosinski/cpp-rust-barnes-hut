use std::time::Instant;
#[cfg(target_arch = "x86_64")]
use std::arch::x86_64::_rdtsc;
use std::fs::File;
use std::io::{self, BufRead};
use std::path::Path;

const NUM_PARTICLES: usize = 10000;
const FRAMES: usize = 300;
const TIME_STEP: f32 = 0.016; 

struct Particle {
    velocity_x: f32,
    velocity_y: f32,
    acc_x: f32,
    acc_y: f32,
    pos_x: f32,
    pos_y: f32,
    mass: f32,
}

fn main() {
    let mut particles: Vec<Particle> = Vec::with_capacity(NUM_PARTICLES);
    
    let path = Path::new("start_10k.txt");
    let file = match File::open(&path) {
        Ok(f) => f,
        Err(_) => {
            eprintln!("Blad: Nie mozna otworzyc pliku start_10k.txt. Czy na pewno wygenerowales plik?");
            std::process::exit(1);
        }
    };
    
    let reader = io::BufReader::new(file);

    for line in reader.lines() {
        let line = line.expect("Blad odczytu linii z pliku");
        
        // Rozdzielamy linię po spacjach
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

    println!(
        "Particle 0 (Start): X={}, Y={}",
        particles[0].pos_x, particles[0].pos_y
    );
    assert!(particles.len() >= NUM_PARTICLES);
    
    let mut total_force_time_ms = 0.0;
    let mut total_cycles_force: u64 = 0;

    for _ in 0..FRAMES {
        
        let start_time = Instant::now();
        let start_cycles = unsafe { _rdtsc() }; 

        for i in 0..NUM_PARTICLES {
            let mut acc_x: f32 = 0.0;
            let mut acc_y: f32 = 0.0;
            let particle_a_pos_x = particles[i].pos_x;
            let particle_a_pos_y = particles[i].pos_y;

            for j in 0..NUM_PARTICLES {
                if i == j {
                    continue;
                }
                let particle_b = &particles[j];
                let dx = particle_b.pos_x - particle_a_pos_x;
                let dy = particle_b.pos_y - particle_a_pos_y;
                let dist_sq = dx * dx + dy * dy; 

                let distance = dist_sq.sqrt();
                
                let acc = particle_b.mass / (dist_sq + 1.0); 

                acc_x += acc * (dx / distance);
                acc_y += acc * (dy / distance);
            }
            particles[i].acc_x = acc_x;
            particles[i].acc_y = acc_y;
        }

        let end_cycles = unsafe { _rdtsc() };
        let end_time = start_time.elapsed();

        total_force_time_ms += end_time.as_secs_f64() * 1000.0;
        total_cycles_force += end_cycles - start_cycles;

        // Całkowanie Euler'a (Aktualizacja pozycji)
        for i in 0..NUM_PARTICLES {
            particles[i].velocity_x += particles[i].acc_x * TIME_STEP;
            particles[i].velocity_y += particles[i].acc_y * TIME_STEP;
            particles[i].pos_x += particles[i].velocity_x * TIME_STEP;
            particles[i].pos_y += particles[i].velocity_y * TIME_STEP;
            
            particles[i].acc_x = 0.0;
            particles[i].acc_y = 0.0;
        }
    }

    println!(
        "| Korzen Masy (Particle 0): X={} Y={}",
        particles[0].pos_x, particles[0].pos_y
    );
    
    println!("WYNIKI WYDAJNOSCIOWE (Srednia z wszystkich klatek)");
    println!("Czas liczenia sil: {:.4} ms / klatke", total_force_time_ms / (FRAMES as f64));
    println!("Cykle liczenia sil: {} cykli / klatke", total_cycles_force / (FRAMES as u64));
}