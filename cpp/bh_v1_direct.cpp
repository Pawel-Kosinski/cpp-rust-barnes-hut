#include <iostream>
#include <vector>
#include "timer.hpp"
#include <fstream>
#include <cmath>
#include <iomanip>
#include "benchmark_options.hpp"

constexpr float G = 1; // Gravitational constant
constexpr float TIME_STEP = 0.016f; // Time step for the simulation

struct Particle
{
    float velocityX{0.0f};
    float velocityY{0.0f};
    float accX{0.0f};
    float accY{0.0f};
    float mass{0.0f};
    float posX{0.0f};
    float posY{0.0f};
};

struct PhysicsMetrics {
    double totalMomentumX = 0.0;
    double totalMomentumY = 0.0;
    double totalKineticEnergy = 0.0;
    double centerX = 0.0;
    double centerY = 0.0;
};

PhysicsMetrics calculatePhysicsDiagnostics(const std::vector<Particle>& particles) {
    PhysicsMetrics m;
    double totalMass = 0.0;

    for (const auto& p : particles) {
        double mass = static_cast<double>(p.mass);
        double vx = static_cast<double>(p.velocityX);
        double vy = static_cast<double>(p.velocityY);
        double px = static_cast<double>(p.posX);
        double py = static_cast<double>(p.posY);

        m.totalMomentumX += mass * vx;
        m.totalMomentumY += mass * vy;
        m.totalKineticEnergy += 0.5 * mass * (vx * vx + vy * vy);

        m.centerX += mass * px;
        m.centerY += mass * py;
        totalMass += mass;
    }

    m.centerX /= totalMass;
    m.centerY /= totalMass;

    return m;
}

int main(int argc, char** argv)
{
    BenchmarkOptions options;
    if (!parseBenchmarkOptions(argc, argv, options)) return argc > 1 ? 1 : 0;

    Timer timer;
    double totalForceTime = 0.0;
    std::vector<Particle> particles;

    std::ifstream inFile(options.input);
    if (!inFile)
    {
        std::cerr << "Error: Could not open file " << options.input << "!\n";
        return 1;
    }

    Particle p;
    p.accX = 0.0f;
    p.accY = 0.0f;
    
    while (inFile >> p.posX >> p.posY >> p.velocityX >> p.velocityY >> p.mass)
    {
        particles.push_back(p);
    }
    inFile.close();
    if (!validateParticleCount(options, particles.size())) return 1;

    for (int frame = 0; frame < options.totalFrames(); ++frame)
    {
        if (frame == 0) {
            size_t particlesMem = particles.capacity() * sizeof(Particle);
            double totalAppMemMB = static_cast<double>(particlesMem) / (1024.0 * 1024.0);
            std::cout << std::fixed << std::setprecision(6);
            std::cout << "Algorithm memory usage: " << totalAppMemMB << " MB\n";
            std::cout << "Size of Particle: " << sizeof(Particle) << " bytes\n";
        }
        timer.start();
        for (std::size_t i = 0; i < particles.size(); ++i)
        {
            float accX = 0.0f;
            float accY = 0.0f;
            for (std::size_t j = 0; j < particles.size(); ++j)
            {
                if (i == j)
                {
                    continue;
                }

                const auto& particleA = particles[i];
                const auto& particleB = particles[j];
                float dx = particleB.posX - particleA.posX;
                float dy = particleB.posY - particleA.posY;
                float distanceSquared = dx * dx + dy * dy;
                if (distanceSquared < 1e-5f) {
                    continue; 
                }
                float distance = sqrt(distanceSquared);

                float acc = G * particleB.mass / (distanceSquared + 1.0f); // Add small value to prevent division by zero

                accX += acc * (dx / distance);

                accY += acc * (dy / distance);

            }

            particles[i].accX += accX;
            particles[i].accY += accY;
        }
        if (frame == options.warmupFrames && !writeForces(options.dumpForces, particles)) return 1;
        for (auto& particle : particles)
        {
            particle.velocityX += particle.accX * TIME_STEP;
            particle.velocityY += particle.accY * TIME_STEP;
            particle.posX += particle.velocityX * TIME_STEP;
            particle.posY += particle.velocityY * TIME_STEP;
            particle.accX = 0.0f;
            particle.accY = 0.0f;
        }
        const double forceTime = timer.stopTime();
        if (frame >= options.warmupFrames) totalForceTime += forceTime;
        if (frame == options.warmupFrames || frame == options.totalFrames() - 1) {
            auto metrics = calculatePhysicsDiagnostics(particles);
            std::cout << "Frame " << frame << ":\n";
            std::cout << "Momentum (" << metrics.totalMomentumX << ", " << metrics.totalMomentumY << ")\n";
            std::cout << "Kinetic energy " << metrics.totalKineticEnergy << "\n";
            std::cout << "Center of mass (" << metrics.centerX << ", " << metrics.centerY << ")\n";
        }
    }
    std::cout << std::fixed << std::setprecision(6);
    std::cout << "Tree construction time: 0.000000 ms / frame\n";
    std::cout << "Force/update time: " << (totalForceTime / options.frames) << " ms / frame\n";
    std::cout << "Cleanup time: 0.000000 ms / frame\n";
    std::cout << "Total measured time: " << totalForceTime << " ms\n";
    return 0;
}
