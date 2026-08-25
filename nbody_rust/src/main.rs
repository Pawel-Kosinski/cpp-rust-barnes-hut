fn main() {
    println!("BHBench-CR Rust benchmark suite");
    println!("Run individual benchmark variants with:");
    println!("  cargo run --release --bin bh_v1_direct");
    println!("  cargo run --release --bin bh_v2_pointer_tree");
    println!("  cargo run --release --bin bh_v3_vector_tree");
    println!("  cargo run --release --bin bh_v4_threaded_tree");
    println!("  cargo run --release --bin bh_v5_parallel_force");
}
