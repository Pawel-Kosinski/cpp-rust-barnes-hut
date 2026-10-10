#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <string>

// The force is 1/(r^2+1), not Plummer softening. Its zero-at-infinity
// pair potential is -m_i*m_j*atan2(1,r), constant below the force cutoff.
template <typename Particles>
class DiagnosticWriter {
    std::ofstream output;
    double dt;
    std::size_t stride;

public:
    DiagnosticWriter(const std::string& path, double timeStep, std::size_t interval)
        : dt(timeStep), stride(interval) {
        if (!path.empty()) {
            output.open(path);
            if (!output) throw std::runtime_error("Cannot open diagnostics: " + path);
            output << "step,time,momentum_x,momentum_y,angular_momentum,kinetic,potential,total_energy\n";
            output << std::setprecision(17);
        }
    }

    void record(std::size_t step, const Particles& particles, bool final = false) {
        if (!output.is_open() || (!final && step % stride != 0)) return;
        double px = 0, py = 0, angular = 0, kinetic = 0, potential = 0;
        for (std::size_t i = 0; i < particles.size(); ++i) {
            const auto& p = particles[i];
            const double m = p.mass, vx = p.velocityX, vy = p.velocityY;
            px += m * vx;
            py += m * vy;
            angular += m * (static_cast<double>(p.posX) * vy - static_cast<double>(p.posY) * vx);
            kinetic += 0.5 * m * (vx * vx + vy * vy);
            for (std::size_t j = 0; j < i; ++j) {
                const double dx = static_cast<double>(p.posX) - particles[j].posX;
                const double dy = static_cast<double>(p.posY) - particles[j].posY;
                const double r = std::sqrt(std::max(dx * dx + dy * dy, 1e-5));
                potential -= m * particles[j].mass * std::atan2(1.0, r);
            }
        }
        output << step << ',' << step * dt << ',' << px << ',' << py << ',' << angular
               << ',' << kinetic << ',' << potential << ',' << kinetic + potential << '\n';
        if (!output) throw std::runtime_error("Failed to write diagnostics");
    }
};

template <typename Particles>
void writeState(const std::string& path, const Particles& particles) {
    if (path.empty()) return;
    std::ofstream output(path);
    if (!output) throw std::runtime_error("Cannot open state snapshot: " + path);
    output << std::setprecision(9);
    for (const auto& p : particles)
        output << p.posX << ' ' << p.posY << ' ' << p.velocityX << ' '
               << p.velocityY << ' ' << p.mass << '\n';
    if (!output) throw std::runtime_error("Failed to write state snapshot");
}

inline void writeMemoryReport(const std::string& path, std::size_t nodes,
    std::size_t nodeBytes, std::size_t treeCapacity, std::size_t treeHeapBlocks,
    std::size_t particleBytes, std::size_t forceBufferBytes) {
    if (path.empty()) return;
    std::ofstream output(path);
    if (!output) throw std::runtime_error("Cannot open memory report: " + path);
    output << "tree_nodes,node_bytes,tree_capacity,tree_heap_blocks,tree_reserved_bytes,particle_reserved_bytes,force_buffer_bytes,structural_bytes\n";
    output << nodes << ',' << nodeBytes << ',' << treeCapacity << ',' << treeHeapBlocks
           << ',' << treeCapacity * nodeBytes << ',' << particleBytes << ',' << forceBufferBytes
           << ',' << treeCapacity * nodeBytes + particleBytes + forceBufferBytes << '\n';
    if (!output) throw std::runtime_error("Failed to write memory report");
}
