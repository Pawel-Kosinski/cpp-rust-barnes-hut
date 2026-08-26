use std::env;
use std::fs::File;
use std::io::{BufWriter, Write};

pub struct BenchmarkOptions {
    pub input: String,
    pub dump_forces: Option<String>,
    pub particles: usize,
    pub frames: usize,
    pub warmup_frames: usize,
    pub theta: f32,
    pub threads: usize,
}

impl Default for BenchmarkOptions {
    fn default() -> Self {
        Self {
            input: "start.txt".to_string(),
            dump_forces: None,
            particles: 0,
            frames: 10,
            warmup_frames: 0,
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
            return Err("Usage: <binary> [--input FILE] [--particles N] [--frames N] [--warmup-frames N] [--theta VALUE] [--threads N] [--dump-forces FILE]".to_string());
        }
        let value = arguments.next().ok_or_else(|| format!("Missing value for {argument}"))?;
        match argument.as_str() {
            "--input" => options.input = value,
            "--dump-forces" => options.dump_forces = Some(value),
            "--particles" => options.particles = value.parse().map_err(|_| "Invalid particle count".to_string())?,
            "--frames" => options.frames = value.parse().map_err(|_| "Invalid frame count".to_string())?,
            "--warmup-frames" => options.warmup_frames = value.parse().map_err(|_| "Invalid warm-up frame count".to_string())?,
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

impl BenchmarkOptions {
    pub fn total_frames(&self) -> usize {
        self.warmup_frames + self.frames
    }
}

pub fn write_forces<I>(path: &str, forces: I) -> Result<(), String>
where
    I: IntoIterator<Item = (f32, f32)>,
{
    let file = File::create(path).map_err(|error| format!("Could not write force snapshot {path}: {error}"))?;
    let mut output = BufWriter::new(file);
    writeln!(output, "index,acc_x,acc_y").map_err(|error| error.to_string())?;
    for (index, (acc_x, acc_y)) in forces.into_iter().enumerate() {
        writeln!(output, "{index},{acc_x:.9},{acc_y:.9}").map_err(|error| error.to_string())?;
    }
    Ok(())
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
