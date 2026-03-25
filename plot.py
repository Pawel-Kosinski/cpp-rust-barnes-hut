import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

N = [100, 1000, 5000, 10000, 25000, 50000]

# Time (ms/frame) = Tree Build Time + Force Calc Time
time_bf = [0.03216, 3.16334, 77.8892, 313.176, 1942.66, 7804.64]
time_4 = [0.04479+0.00446, 1.51026+0.07850, 10.6211+0.4392, 17.6032+0.9624, 77.7249+2.8806, 188.136+6.6627]
time_5 = [0.01214+0.00773, 0.18511+0.1074, 1.35749+0.6056, 2.19907+1.3010, 9.9481+3.6158, 23.6565+8.1103]

# Cycles/frame = Tree Build Cycles + Force Calc Cycles
cyc_bf = [124394, 11999704, 295418240, 1187799552, 7368065536, 29601247232]
cyc_4 = [18672+171571, 299447+5729887, 1667756+40285148, 3652086+66766144, 10927578+294794848, 25271880+713557952]
cyc_5 = [30952+47834, 408981+703900, 2299037+5150315, 4936058+8342312, 13715581+37732592, 30762414+89725672]

# --- PLOT 1: Time vs N ---
plt.figure(figsize=(10, 6))
plt.plot(N, time_bf, 'o-', color='red', label='Brute Force (O(N^2))')
plt.plot(N, time_4, 's-', color='blue', label='Wersja 4 (Wektor jednowątkowo)')
plt.plot(N, time_5, '^-', color='green', label='Wersja 5 (OpenMP wielowątkowo)')
plt.xscale('log')
plt.yscale('log')
plt.title('Czas obliczeń jednej klatki w zależności od liczby cząstek (N)', fontsize=14)
plt.xlabel('Liczba cząstek (N)', fontsize=12)
plt.ylabel('Czas całkowity (ms) - skala logarytmiczna', fontsize=12)
plt.grid(True, which="both", ls="--", alpha=0.5)
plt.legend(fontsize=12)
plt.tight_layout()
plt.savefig('time_vs_n.png')
plt.close()

# --- PLOT 2: Cycles vs N ---
plt.figure(figsize=(10, 6))
plt.plot(N, cyc_bf, 'o-', color='red', label='Brute Force')
plt.plot(N, cyc_4, 's-', color='blue', label='Wersja 4 (Jednowątkowo)')
plt.plot(N, cyc_5, '^-', color='green', label='Wersja 5 (Wielowątkowo)')
plt.xscale('log')
plt.yscale('log')
plt.title('Liczba cykli procesora na klatkę w zależności od liczby cząstek (N)', fontsize=14)
plt.xlabel('Liczba cząstek (N)', fontsize=12)
plt.ylabel('Cykle na klatkę - skala logarytmiczna', fontsize=12)
plt.grid(True, which="both", ls="--", alpha=0.5)
plt.legend(fontsize=12)
plt.tight_layout()
plt.savefig('cycles_vs_n.png')
plt.close()

# --- PLOT 3: Theta vs Time and Error (N=10000, Prog 4) ---
theta_vals = [0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5]
theta_times = [0.979+1165.15, 1.002+495.07, 0.977+192.64, 0.982+71.93, 0.973+39.26, 0.988+25.19, 0.991+18.11]
theta_errors = [1.725, 1.734, 2.038, 2.971, 3.418, 3.895, 4.525]

fig, ax1 = plt.subplots(figsize=(10, 6))

color = 'tab:blue'
ax1.set_xlabel('Wartość parametru Theta', fontsize=12)
ax1.set_ylabel('Czas na klatkę (ms)', color=color, fontsize=12)
ax1.plot(theta_vals, theta_times, 'o-', color=color, linewidth=2)
ax1.tick_params(axis='y', labelcolor=color)
ax1.grid(True, ls="--", alpha=0.5)

ax2 = ax1.twinx()  
color = 'tab:red'
ax2.set_ylabel('Średni błąd pozycji (MAE)', color=color, fontsize=12)  
ax2.plot(theta_vals, theta_errors, 's-', color=color, linewidth=2)
ax2.tick_params(axis='y', labelcolor=color)

plt.title('Wpływ parametru Theta na czas i błąd (N=10000, Wersja 4)', fontsize=14)
fig.tight_layout()  
plt.savefig('theta_tradeoff.png')
plt.close()