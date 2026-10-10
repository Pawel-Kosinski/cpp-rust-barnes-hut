#include "benchmark_options.hpp"
#include <cmath>
#include <vector>

// Independent double-precision direct summation at selected targets, with the
// same float32 input rounding and cutoff as the ten benchmark implementations.
int main(int argc, char** argv) {
    BenchmarkOptions options;
    if (!parseBenchmarkOptions(argc, argv, options)) return 1;
    struct Particle { double x, y, mass; };
    std::vector<Particle> particles;
    std::ifstream input(options.input);
    float x, y, vx, vy, mass;
    while (input >> x >> y >> vx >> vy >> mass) particles.push_back({x, y, mass});
    if (!validateParticleCount(options, particles.size()) || options.dumpForces.empty()) return 1;
    std::ofstream output(options.dumpForces);
    if (!output) return 1;
    output << "index,acc_x,acc_y\n" << std::setprecision(17);
    const auto count = options.forceSamples == 0 ? particles.size() : std::min(options.forceSamples, particles.size());
    for (std::size_t k = 0; k < count; ++k) {
        const auto index = count <= 1 ? 0 : k * (particles.size() - 1) / (count - 1);
        const auto& target = particles[index];
        double ax = 0, ay = 0;
        for (std::size_t j = 0; j < particles.size(); ++j) {
            if (j == index) continue;
            const auto& source = particles[j];
            const double dx = source.x - target.x, dy = source.y - target.y;
            const double r2 = dx * dx + dy * dy;
            if (r2 < 1e-5) continue;
            const double factor = source.mass / ((r2 + 1.0) * std::sqrt(r2));
            ax += factor * dx;
            ay += factor * dy;
        }
        output << index << ',' << ax << ',' << ay << '\n';
    }
    output.flush();
    return output ? 0 : 1;
}
