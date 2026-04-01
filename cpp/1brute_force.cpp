#include <iostream>
#include <vector>
#include "timer.hpp"
#include <fstream>
#include <cmath>

constexpr float G = 1; // Gravitational constant
constexpr float TIME_STEP = 0.016f; // Time step for the simulation
constexpr float FRAMES = 300;
constexpr int NUM_PARTICLES = 10000;

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



int main()
{
    srand(42);
    Timer timer;
    float time = 0.0f;
    std::vector<Particle> particles;
    unsigned long long totalCycles = 0;
    particles.reserve(NUM_PARTICLES);

    std::ifstream inFile("start_10k.txt");
    if (!inFile)
    {
        std::cerr << "Blad: Nie mozna otworzyc pliku start_10k.txt!\n";
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
    }
    std::cout << " | Korzen Masy: X=" << particles[0].posX << " Y=" << particles[0].posY << std::endl;
    std::cout << "Czas liczenia sil:  " << (time / FRAMES) << " ms / klatke\n";
    std::cout << "Calkowity czas symulacji: " << (time) << " ms\n";
    std::cout << "Cykle liczenia sil:  " << std::fixed << (totalCycles / FRAMES) << " cykli / klatke\n";

    std::ofstream outFile("wzorzec_10k.txt");
    for (const auto& p : particles)
    {
        outFile << p.posX << " " << p.posY << "\n";
    }
    outFile.close();
    std::cout << "Zapisano pozycje referencyjne do pliku wzorzec_10k.txt\n";
    return 0;
}