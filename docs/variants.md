# Solver variants

This repository contains five two-dimensional Barnes-Hut / N-body solver variants implemented in C++ and Rust.

## V1: Direct summation

Baseline O(N^2) force calculation. It is used as a reference for accuracy measurements and as a simple lower-level implementation baseline.

## V2: Pointer-based quadtree

A Barnes-Hut quadtree using pointer-based node allocation. This version is retained as a deliberately simple locality baseline.

All Barnes-Hut variants descend into any node that geometrically contains the target particle, so an accepted aggregate can never include the target itself. Leaves keep coincident particles in an index chain, evaluate their sources directly, and do not perturb input coordinates.

## V3: Contiguous index-based quadtree

A Barnes-Hut quadtree stored in a contiguous vector/arena. Child relationships are represented with integer indices rather than pointers. Its C++ `NodeV3` layout intentionally has no threaded-traversal field, matching the Rust V3 structure.

## V4: Iterative threaded tree traversal

A recursion-free traversal using an additional next-node index. C++ and Rust both add this field only in V4/V5, so the V3-to-V4 layout change is matched across languages.

## V5: Parallel force evaluation

A parallel force-evaluation variant. The C++ implementation uses OpenMP, and the Rust implementation uses Rayon. Tree construction remains serial.
