#include <iostream>
#include <vector>
#include "timer.hpp"
#include <fstream>
#include <cmath>
#include <iomanip>

constexpr float G = 1; // Gravitational constant
constexpr float TIME_STEP = 0.016f; // Time step for the simulation
constexpr float FRAMES = 300;
constexpr int NUM_PARTICLES = 50000;

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

int main()
{
    srand(42);
    Timer timer;
    float time = 0.0f;
    std::vector<Particle> particles;
    unsigned long long totalCycles = 0;
    //particles.reserve(NUM_PARTICLES);

    std::ifstream inFile("start_50k.txt");
    if (!inFile)
    {
        std::cerr << "Error: Could not open file start_100k.txt!\n";
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
    for (int frame = 0; frame < FRAMES; ++frame)
    {
        if (frame == 0) {
            size_t particlesMem = particles.capacity() * sizeof(Particle);
            double totalAppMemMB = static_cast<double>(particlesMem) / (1024.0 * 1024.0);
            std::cout << std::fixed << std::setprecision(6);
            std::cout << "Algorithm memory usage: " << totalAppMemMB << " MB\n";
            std::cout << "Size of Particle: " << sizeof(Particle) << " bytes\n";
        }
        timer.start();
        for (int i = 0; i < NUM_PARTICLES; ++i)
        {
            float accX = 0.0f;
            float accY = 0.0f;
            for (int j = 0; j < NUM_PARTICLES; ++j)
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
        time += timer.stopTime();
        totalCycles += timer.stopCycles();
        for (auto& particle : particles)
        {
            particle.velocityX += particle.accX * TIME_STEP;
            particle.velocityY += particle.accY * TIME_STEP;
            particle.posX += particle.velocityX * TIME_STEP;
            particle.posY += particle.velocityY * TIME_STEP;
            particle.accX = 0.0f;
            particle.accY = 0.0f;
        }
        if (frame == 0 or frame == FRAMES - 1) {
            auto metrics = calculatePhysicsDiagnostics(particles);
            std::cout << "Frame " << frame << ":\n";
            std::cout << "Ped (" << metrics.totalMomentumX << ", " << metrics.totalMomentumY << ")\n";
            std::cout << "Energia kinetyczna " << metrics.totalKineticEnergy << "\n";
            std::cout << "Srodek masy (" << metrics.centerX << ", " << metrics.centerY << ")\n";
        }
    }
    std::cout << "Force calculation time:  " << (time / FRAMES) << " ms / frame\n";
    std::cout << "Total simulation time: " << (time) << " ms\n";
    std::cout << "Force calculation cycles:  " << std::fixed << (totalCycles / FRAMES) << " cycles / frame\n";

    std::ofstream outFile("reference_50k.txt");
    outFile << std::fixed << std::setprecision(6);
    for (const auto& p : particles)
    {
        outFile << p.posX << " " << p.posY << "\n";
    }
    outFile.close();
    std::cout << "Saved reference positions to file reference_50k.txt\n";
    return 0;
}