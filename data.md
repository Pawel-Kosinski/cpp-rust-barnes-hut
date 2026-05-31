# 
# FIGURE 1: Algorithmic Scaling (V1 Brute-Force vs V4 Threaded Tree)

N_particles_fig1 = [100, 1000, 5000, 10000, 20000, 50000]

# EXECUTION TIME (ms)
time_cpp_v1 = [0.025, 2.454, 62.075, 248.802, 993.714, 6168.958]

time_cpp_v4 = [0.050, 1.698, 11.451, 25.574, 57.555, 160.160]

time_rust_v1 = [0.024, 2.415, 60.541, 243.709, 978.152, 6126.958]

time_rust_v4 = [0.045, 1.595, 11.214, 25.035, 57.579, 170.960]

# CPU CYCLES (Millions)
cycles_cpp_v1 = [0.096, 9.310, 235.437, 943.562, 3768.932, 23397.316]

cycles_cpp_v4 = [0.194, 6.446, 43.435, 97.001, 218.298, 607.440]

cycles_rust_v1 = [0.093, 9.162, 229.618, 924.330, 3709.901, 23238.125]

cycles_rust_v4 = [0.173, 6.051, 42.533, 94.954, 218.386, 659.810]


# 
# FIGURE 2: Impact of Architectural Optimizations (N=50,000)

labels_fig2 = ['V2 (Pointers)', 'V3 (Vector)', 'V4 (Threaded Tree)', 'V5 (Threads)']

# EXECUTION TIME per frame (ms)
time_cpp_fig2 = [177.7, 164.6, 160.2, 26.4]

time_rust_fig2 = [179.4, 175.0, 171.0, 28.1]

# CPU CYCLES (Millions)
cycles_cpp_fig2 = [674.0, 624.3, 607.4, 100.6]

cycles_rust_fig2 = [680.4, 663.8, 659.8, 109.8]


# 
# FIGURE 3: Impact of Memory Architecture at Scale (N=500,000)
labels_fig3 = ['V2 (Pointers)', 'V3 (Vector)', 'V4 (Threaded)', 'V5 (Threads)']

# EXECUTION TIME per frame (ms)
time_cpp_fig3 = [3690.2, 2778.6, 3094.5, 529.7]

time_rust_fig3 = [3749.5, 3349.7, 3571.1, 559.1]

# CPU CYCLES (Millions)
cycles_cpp_fig3 = [13996.0, 10539.4, 11736.5, 2013.7]

cycles_rust_fig3 = [14221.2, 12704.8, 13544.2, 2122.8]


# 
# FIGURE 4: High-Performance Scaling & Concurrency (10k to 1M)

N_particles_fig4 = [10000, 20000, 50000, 100000, 500000, 1000000]

# EXECUTION TIME (ms) - V4 and V5
time_cpp_v4_fig4 = [25.57, 57.55, 160.16, 361.88, 3094.50, 7525.60]

time_rust_v4_fig4 = [25.03, 57.57, 170.96, 387.18, 3571.10, 8818.60]

time_cpp_v5_fig4 = [5.04, 10.11, 27.95, 65.51, 529.70, 1226.50]

time_rust_v5_fig4 = [4.15, 9.25, 26.11, 66.70, 559.10, 1324.10]

# CPU CYCLES (Millions) - V4 and V5
cycles_cpp_v4_fig4 = [97.00, 218.29, 607.44, 1372.54, 11736.51, 28543.61]

cycles_rust_v4_fig4 = [94.95, 218.38, 659.81, 1468.49, 13544.22, 33446.88]

cycles_cpp_v5_fig4 = [19.12, 38.33, 106.00, 248.43, 2013.70, 4651.68]

cycles_rust_v5_fig4 = [15.74, 35.08, 99.03, 252.97, 2122.80, 5022.10]


# 
# TABLE 1 & 2: Impact of theta on accuracy and performance (N = 10,000)

theta_values = [0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5]

# C++
time_cpp_theta = [1310.13, 534.03, 203.58, 73.28, 42.65, 27.68, 20.77]

mae_pos_cpp_theta = [0.0075, 0.0086, 0.0127, 0.0363, 0.0817, 0.1534, 0.2453]

max_pos_err_cpp_theta = [0.945, 0.943, 0.941, 0.910, 1.073, 2.425, 2.582]

avg_force_err_cpp_theta = [0.002, 0.007, 0.039, 0.199, 0.495, 0.937, 1.526]

max_force_err_cpp_theta = [8.201, 1.712, 2.074, 34.722, 47.184, 54.035, 92.030]

# RUST
time_rust_theta = [1433.54, 557.55, 216.77, 76.60, 42.29, 28.42, 21.48]

mae_pos_rust_theta = [0.0087, 0.0098, 0.0138, 0.0368, 0.0819, 0.1536, 0.2453]

max_pos_err_rust_theta = [0.945, 0.944, 0.942, 0.911, 1.070, 2.425, 2.580]

avg_force_err_rust_theta = [0.002, 0.007, 0.039, 0.199, 0.495, 0.937, 1.526]

max_force_err_rust_theta = [8.201, 1.712, 2.074, 34.722, 47.184, 54.035, 92.030]


# 
# TABLE 3: Strong Scaling Performance (N = 10,000)

threads_10k = [1, 2, 4, 6, 8, 12, 16, 32]

# C++
time_cpp_scaling_10k = [24.61, 12.66, 6.56, 4.75, 3.81, 2.87, 2.92, 2.92]

speedup_cpp_scaling_10k = [1.00, 1.94, 3.74, 5.17, 6.44, 8.56, 8.42, 8.42]

# RUST
time_rust_scaling_10k = [24.90, 12.91, 6.49, 4.57, 3.89, 2.99, 3.22, 3.33]

speedup_rust_scaling_10k = [1.00, 1.93, 3.83, 5.45, 6.39, 8.32, 7.73, 7.47]


# 
# TABLE 4: Strong Scaling Performance (N = 1,000,000)

threads_1m = [1, 2, 4, 6, 8, 12, 16, 32]

# C++
time_cpp_scaling_1m = [8046.59, 4268.55, 2329.85, 1463.64, 1159.62, 928.35, 903.08, 867.72]

speedup_cpp_scaling_1m = [1.00, 1.88, 3.45, 5.49, 6.93, 8.66, 8.91, 9.27]

# RUST
time_rust_scaling_1m = [9846.54, 5489.58, 2730.44, 1825.43, 1284.87, 955.71, 942.21, 954.79]

speedup_rust_scaling_1m = [1.00, 1.79, 3.61, 5.39, 7.66, 10.30, 10.45, 10.31]


# 
# TABLE 5: Algorithmic Memory Consumption at N = 1,000,000
memory_impl_labels = ['V2 (Pointer tree)', 'V3 (Vector tree)', 'V4/V5 (Threaded tree)']

memory_cpp_mb = [202.78, 165.33, 165.33]

memory_rust_mb = [204.08, 202.00, 234.00]

memory_difference_mb = [1.30, 36.67, 68.67]


# 
# TABLE 6: Safe versus unsafe Rust indexing
bounds_config_labels = ['V4, N=100,000', 'V5, N=500,000']

bounds_safe_rust_mean_ms = [356.25, 355.22]

bounds_safe_rust_std_ms = [1.92, 0.73]

bounds_unsafe_rust_mean_ms = [362.05, 355.14]

bounds_unsafe_rust_std_ms = [12.71, 0.73]

bounds_difference_percent = [1.63, -0.02]