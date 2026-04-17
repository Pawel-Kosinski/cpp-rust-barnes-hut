#![allow(non_snake_case)]

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
        let mut shift = 0.0001;
        while particles[pIdx].pos_x == particles[oldIdx].pos_x && particles[pIdx].pos_y == particles[oldIdx].pos_y 
        {
            particles[pIdx].pos_x += shift;
            shift *= 2.0; // Zwiększamy przesunięcie dwukrotnie, aż 'f32' to zarejestruje
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
        let pIdx = node.particle_index;
        node.mass = particles[pIdx].mass;
        node.center_of_mass_x = particles[pIdx].pos_x;
        node.center_of_mass_y = particles[pIdx].pos_y;
    }
    
}

fn calculateForcesPtr(pIdx: usize, node: &NodePtr, particles: &mut Vec<Particle>)
{
    let p: &Particle = &particles[pIdx];
    let dx = node.center_of_mass_x - p.pos_x;
    let dy = node.center_of_mass_y - p.pos_y;
    let dist_sq = dx * dx + dy * dy;
    let dist = dist_sq.sqrt();

    if dist_sq < 1e-5 {return;}

    let s = node.half_size * 2.0;

    if (s / dist) < THETA || node.children[0].is_none()
    {
        let acc = G *node.mass / (dist_sq + 1.0);
        particles[pIdx].acc_x += acc * (dx / dist);
        particles[pIdx].acc_y += acc * (dy / dist);
    }
    else
    {
        for i in 0..4
        {
            calculateForcesPtr(pIdx, node.children[i].as_ref().unwrap(), particles);
        }
    }
}

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
 
fn main()
{
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

    let mut total_force_time_ms = 0.0;
    let mut total_tree_time_ms = 0.0;
    let mut total_cycles_force: u64 = 0;
    let mut total_cycles_tree: u64 = 0;

    for i in 0..FRAMES {
        
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

        let mut root: NodePtr = NodePtr::default();
        root.bounds_x = centerX;
        root.bounds_y = centerY;
        root.half_size = maxHalfSize;

        for j in 0..NUM_PARTICLES
        {
            insertParticlePtr(&mut root, j, &mut particles);
        }
        if i == 0 {
            let particlesMem: usize = particles.capacity() * std::mem::size_of::<Particle>();
            let nodeCount = countNodesPtr(&root);
            let treeMem = (nodeCount as usize) * std::mem::size_of::<NodePtr>();
            let totalAppMemMB = (particlesMem + treeMem) as f64 / (1024.0 * 1024.0);

            println!("Zuzycie pamieci algorytmu: {} MB", totalAppMemMB);
            println!("Stworzono {} wezlow drzewa", nodeCount);
        }

        computeMassDistributionPtr(&mut root, &particles);
        total_tree_time_ms += start_time.elapsed().as_secs_f64() * 1000.0;
        total_cycles_tree += unsafe { _rdtsc() } - start_cycles;

        start_time = Instant::now();
        start_cycles = unsafe { _rdtsc() };
        for k in 0..NUM_PARTICLES
        {
            calculateForcesPtr(k, &root, &mut particles);
        }

        for p in &mut particles
        {
            p.velocity_x += p.acc_x * TIME_STEP;
            p.velocity_y += p.acc_y * TIME_STEP;
            p.pos_x += p.velocity_x * TIME_STEP;
            p.pos_y += p.velocity_y * TIME_STEP;
            p.acc_x = 0.0;
            p.acc_y = 0.0;
        }

        total_force_time_ms += start_time.elapsed().as_secs_f64() * 1000.0;
        total_cycles_force += unsafe { _rdtsc() } - start_cycles;
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
            let mut current_error = 0.0f32;
            let mut max_error = 0.0f32;

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
                    current_error = (dx * dx + dy * dy).sqrt();
                    total_error += current_error;
                    if current_error > max_error {
                        max_error = current_error;
                    }
                    particle_count += 1;
                }
            }

            if particle_count > 0 {
                let mean_absolute_error = total_error / particle_count as f32;
                println!("Sredni blad pozycji (MAE): {} jednostek", mean_absolute_error);
                println!("Maksymalny blad pozycji: {} jednostek", max_error);
            }
        }
        Err(_) => {
            eprintln!("file error.");
        }
    }
}

