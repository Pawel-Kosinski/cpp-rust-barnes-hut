#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <string>

constexpr float PI = 3.14159265359f;
constexpr float G = 1.0f;

float unitInterval(std::mt19937& rng)
{
    constexpr double scale = 1.0 / 4294967296.0;
    return static_cast<float>(static_cast<double>(rng()) * scale);
}

int main(int argc, char** argv)
{
    std::size_t numParticles = 50000;
    std::string outputFile = "start_50k.txt";
    std::uint32_t seed = 1337;
    const std::string distribution = argc >= 5 ? argv[4] : "plummer";
    if (distribution != "plummer" && distribution != "uniform" && distribution != "clustered") {
        std::cerr << "Distribution must be plummer, uniform, or clustered.\n";
        return 1;
    }

    if (argc >= 2) {
        numParticles = static_cast<std::size_t>(std::stoull(argv[1]));
    }

    if (argc >= 3) {
        outputFile = argv[2];
    }

    if (argc >= 4) {
        seed = static_cast<std::uint32_t>(std::stoul(argv[3]));
    }

    std::mt19937 rng(seed);

    std::ofstream outFile(outputFile);
    if (!outFile) {
        std::cerr << "Error while writing the file: " << outputFile << "\n";
        return 1;
    }

    const float centerX = 500.0f;
    const float centerY = 500.0f;
    const float a = 100.0f;
    const float maxRadius = 400.0f;
    const float particleMass = 2.0f;

    const float totalMass = static_cast<float>(numParticles) * particleMass;

    outFile << std::fixed << std::setprecision(6);

    for (std::size_t i = 0; i < numParticles; ++i)
    {
        float r;

        // Correct tail truncation by rejection sampling.
        // Instead of clamping particles to the boundary, sample until accepted.
        do {
            float u = unitInterval(rng);
            if (distribution == "plummer") u = std::min(u, 0.999f);
            r = distribution == "plummer" ? a * std::sqrt(u / (1.0f - u))
                                         : maxRadius * std::sqrt(u);
        } while (r > maxRadius);

        const float theta = unitInterval(rng) * 2.0f * PI;

        float posX = centerX + r * std::cos(theta);
        float posY = centerY + r * std::sin(theta);
        if (distribution == "clustered") {
            // Four Gaussian clusters; this is a workload, not an equilibrium model.
            const float radius = 25.0f * std::sqrt(-2.0f * std::log(std::max(unitInterval(rng), 1e-7f)));
            const std::size_t cluster = i % 4;
            posX = centerX + (cluster & 1 ? 140.0f : -140.0f) + radius * std::cos(theta);
            posY = centerY + (cluster & 2 ? 140.0f : -140.0f) + radius * std::sin(theta);
        }

        // Orbital velocity initialization.
        // Compute enclosed mass within radius r for the 2D Plummer distribution.
        const float massEnclosed = totalMass * (r * r) / (r * r + a * a);

        // Circular-orbit velocity formula with softened denominator.
        const float vCirc = std::sqrt((G * massEnclosed) / (r + 0.1f));

        // Small perturbation used to break perfect symmetry (+/- 15%).
        const float perturbation = 0.85f + unitInterval(rng) * 0.30f;
        const float v = vCirc * perturbation;

        const float velocityX = -v * std::sin(theta);
        const float velocityY =  v * std::cos(theta);

        outFile << posX << " " << posY << " "
                << velocityX << " " << velocityY << " "
                << particleMass << "\n";
    }

    std::cout << "Generated " << numParticles
              << " " << distribution << "-distribution particles in "
              << outputFile << "\n";

    return 0;
}
