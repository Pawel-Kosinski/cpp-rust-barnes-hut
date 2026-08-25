use std::env;

pub struct BenchmarkOptions {
    pub input: String,
    pub particles: usize,
    pub frames: usize,
    pub theta: f32,
    pub threads: usize,
}

impl Default for BenchmarkOptions {
    fn default() -> Self {
        Self {
            input: "start.txt".to_string(),
            particles: 0,
            frames: 10,
            theta: 0.3,
            threads: 0,
        }
    }
}

pub fn parse_options() -> Result<BenchmarkOptions, String> {
    let mut options = BenchmarkOptions::default();
    let mut arguments = env::args().skip(1);
    while let Some(argument) = arguments.next() {
        if argument == "--help" {
            return Err("Usage: <binary> [--input FILE] [--particles N] [--frames N] [--theta VALUE] [--threads N]".to_string());
        }
        let value = arguments.next().ok_or_else(|| format!("Missing value for {argument}"))?;
        match argument.as_str() {
            "--input" => options.input = value,
            "--particles" => options.particles = value.parse().map_err(|_| "Invalid particle count".to_string())?,
            "--frames" => options.frames = value.parse().map_err(|_| "Invalid frame count".to_string())?,
            "--theta" => options.theta = value.parse().map_err(|_| "Invalid theta".to_string())?,
            "--threads" => options.threads = value.parse().map_err(|_| "Invalid thread count".to_string())?,
            _ => return Err(format!("Unknown option: {argument}")),
        }
    }
    if options.frames == 0 || options.theta <= 0.0 {
        return Err("frames and theta must be positive".to_string());
    }
    Ok(options)
}

pub fn validate_particle_count(options: &BenchmarkOptions, loaded: usize) -> Result<(), String> {
    if loaded == 0 {
        return Err("Input contains no particles".to_string());
    }
    if options.particles != 0 && options.particles != loaded {
        return Err(format!("Input contains {loaded} particles but --particles requested {}", options.particles));
    }
    Ok(())
}
