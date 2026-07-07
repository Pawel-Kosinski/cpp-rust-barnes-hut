# N-Body Benchmarks

Short build instructions for Rust and C++.

## Rust

Run a binary in release mode:

```bash
cargo run --release --bin 4
```

## C++

Build examples:

```bash
clang++ -O3 .\4without_recursion.cpp -o 4
clang++ -O3 -fopenmp .\5multi_thread.cpp -o 5
```
