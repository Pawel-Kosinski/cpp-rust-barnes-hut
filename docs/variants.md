# Solver variants

This repository contains five two-dimensional Barnes-Hut / N-body solver variants implemented in C++ and Rust.

## V1: Direct summation

Baseline O(N^2) force calculation. It is used as a reference for accuracy measurements and as a simple lower-level implementation baseline.

## V2: Pointer-based quadtree

A Barnes-Hut quadtree using pointer-based node allocation. This version is retained as a deliberately simple locality baseline.

## V3: Contiguous index-based quadtree

A Barnes-Hut quadtree stored in a contiguous vector/arena. Child relationships are represented with integer indices rather than pointers.

## V4: Iterative threaded tree traversal

A recursion-free traversal using an additional next-node index. This variant evaluates the trade-off between reduced traversal-control overhead and increased node size.

## V5: Parallel force evaluation

A parallel force-evaluation variant. The C++ implementation uses OpenMP, and the Rust implementation uses Rayon. Tree construction remains serial.
