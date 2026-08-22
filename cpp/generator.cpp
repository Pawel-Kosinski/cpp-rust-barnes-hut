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

int main(int argc, char** argv)
{
    std::size_t numParticles = 50000;
    std::string outputFile = "start_50k.txt";
    std::uint32_t seed = 1337;

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
    std::uniform_real_distribution<float> dist(0.0f, 1.0f);

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
            float u = dist(rng);
            u = std::min(u, 0.999f);
            r = a * std::sqrt(u / (1.0f - u));
        } while (r > maxRadius);

        const float theta = dist(rng) * 2.0f * PI;

        const float posX = centerX + r * std::cos(theta);
        const float posY = centerY + r * std::sin(theta);

        // Orbital velocity initialization.
        // Compute enclosed mass within radius r for the 2D Plummer distribution.
        const float massEnclosed = totalMass * (r * r) / (r * r + a * a);

        // Circular-orbit velocity formula with softened denominator.
        const float vCirc = std::sqrt((G * massEnclosed) / (r + 0.1f));

        // Small perturbation used to break perfect symmetry (+/- 15%).
        const float perturbation = 0.85f + dist(rng) * 0.30f;
        const float v = vCirc * perturbation;

        const float velocityX = -v * std::sin(theta);
        const float velocityY =  v * std::cos(theta);

        outFile << posX << " " << posY << " "
                << velocityX << " " << velocityY << " "
                << particleMass << "\n";
    }

    std::cout << "Generated " << numParticles
              << " Plummer-distribution particles in "
              << outputFile << "\n";

    return 0;
}
