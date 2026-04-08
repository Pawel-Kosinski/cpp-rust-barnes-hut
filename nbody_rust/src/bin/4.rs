#![allow(non_snake_case)]

use std::os::windows::thread;
use std::time::Instant;
#[cfg(target_arch = "x86_64")]
use std::arch::x86_64::_rdtsc;
use std::fs::File;
use std::io::{self, BufRead};
use std::path::Path;

const NUM_PARTICLES: usize = 10000;
const FRAMES: usize = 300;
const TIME_STEP: f32 = 0.016; 
const THETA: f32 = 0.4;
const G : f32 = 1.0;

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
    //let node = &mut arena[nodeIdx];
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
        arena[nodeIdx].children[i] = arena.len();

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
    //let node = &mut arena[nodeIdx];
    if arena[nodeIdx].children[0] != usize::MAX
    {
        arena[nodeIdx].mass = 0.0;
        arena[nodeIdx].center_of_mass_x = 0.0;
        arena[nodeIdx].center_of_mass_y = 0.0;

        for i in 0..4
        {
            let childIdx = arena[nodeIdx].children[i];
            computeMassDistribution(childIdx, arena, particles);
            //let child = &arena[childIdx];
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


fn calculateForces(pIdx: usize, nodeIdx: usize, arena: &Vec<Node>, particles: &mut Vec<Particle>)
{
    if nodeIdx == usize::MAX {return;}

    let mut currNodeIdx: usize = 0;
    while currNodeIdx != usize::MAX
    {
        let node = &arena[currNodeIdx];
        let dx = node.center_of_mass_x - particles[pIdx].pos_x;
        let dy = node.center_of_mass_y - particles[pIdx].pos_y;
        let dist_sq = dx * dx + dy * dy;
        let dist = dist_sq.sqrt();

        if dist_sq < 1e-5 {
            currNodeIdx = node.next;
            continue;
        }

        let s = node.half_size * 2.0;

        if (s / dist) < THETA || node.children[0] == usize::MAX
        {
            let acc = G * node.mass / (dist_sq + 1.0);
            particles[pIdx].acc_x += acc * (dx / dist);
            particles[pIdx].acc_y += acc * (dy / dist);
            currNodeIdx = node.next;
        }
        else
        {
            currNodeIdx = node.children[0];
        }
    }
}
 
fn main()
{
    let mut particles: Vec<Particle> = Vec::with_capacity(NUM_PARTICLES);
    let mut arena: Vec<Node> = Vec::with_capacity(10 * NUM_PARTICLES);
    
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

    let mut total_force_time_ms = 0.0;
    let mut total_tree_time_ms = 0.0;
    let mut total_cycles_force: u64 = 0;
    let mut total_cycles_tree: u64 = 0;

    for _ in 0..FRAMES {
        
        let mut start_time = Instant::now();
        let mut start_cycles = unsafe { _rdtsc() }; 

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

        for i in 0..NUM_PARTICLES
        {
            insertParticle(0, i, &mut arena, &mut particles);
        }

        computeMassDistribution(0, &mut arena, &particles);
        threadTree(0, usize::MAX, &mut arena);
        total_tree_time_ms += start_time.elapsed().as_secs_f64() * 1000.0;
        total_cycles_tree += unsafe { _rdtsc() } - start_cycles;

        start_time = Instant::now();
        start_cycles = unsafe { _rdtsc() };
        for i in 0..NUM_PARTICLES
        {
            calculateForces(i, 0, &mut arena, &mut particles);
        }
        total_force_time_ms += start_time.elapsed().as_secs_f64() * 1000.0;
        total_cycles_force += unsafe { _rdtsc() } - start_cycles;

        for p in &mut particles
        {
            p.velocity_x += p.acc_x * TIME_STEP;
            p.velocity_y += p.acc_y * TIME_STEP;
            p.pos_x += p.velocity_x * TIME_STEP;
            p.pos_y += p.velocity_y * TIME_STEP;
            p.acc_x = 0.0;
            p.acc_y = 0.0;
        }
}

    println!("Czas liczenia sil: {:.4} ms / klatke", total_force_time_ms / (FRAMES as f64));
    println!("Cykle liczenia sil: {} cykli / klatke", total_cycles_force / (FRAMES as u64));
    println!("Calkowity czas symulacji: {:.4} ms", (total_force_time_ms + total_tree_time_ms));
    println!("Czas budowy drzewa: {:.4} ms / klatke", total_tree_time_ms / (FRAMES as f64));
    println!("Cykle budowy drzewa: {} cykli / klatke", total_cycles_tree / (FRAMES as u64));

    let ref_path = Path::new("wzorzec_10k.txt");
    match File::open(&ref_path) {
        Ok(ref_file) => {
            let ref_reader = io::BufReader::new(ref_file);
            let mut total_error = 0.0f32;
            let mut particle_count = 0usize;

            for (idx, line) in ref_reader.lines().enumerate() {
                if idx >= NUM_PARTICLES {
                    break;
                }
                
                let line = match line {
                    Ok(l) => l,
                    Err(_) => break,
                };

                let parts: Vec<&str> = line.split_whitespace().collect();
                if parts.len() >= 2 {
                    let ref_x: f32 = match parts[0].parse() {
                        Ok(x) => x,
                        Err(_) => break,
                    };
                    let ref_y: f32 = match parts[1].parse() {
                        Ok(y) => y,
                        Err(_) => break,
                    };

                    let dx = particles[idx].pos_x - ref_x;
                    let dy = particles[idx].pos_y - ref_y;
                    total_error += (dx * dx + dy * dy).sqrt();
                    particle_count += 1;
                }
            }

            if particle_count > 0 {
                let mean_absolute_error = total_error / particle_count as f32;
                println!("Sredni blad pozycji (MAE): {} jednostek", mean_absolute_error);
            }
        }
        Err(_) => {
            eprintln!("file error.");
        }
    }
}

