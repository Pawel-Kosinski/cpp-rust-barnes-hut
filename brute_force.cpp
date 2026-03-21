#include <iostream>
#include <vector>

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



int main()

{
    std::vector<Particle> particles;
    //create vector with random generated particles with a random distribution
    for (uint8_t i = 0; i < 100; ++i)
    {

        Particle p;
        p.velocityX = static_cast<float>(rand()) / RAND_MAX * 50.0f; // Random velocity between 0 and 50
        p.velocityY = static_cast<float>(rand()) / RAND_MAX * 50.0f; // Random velocity between 0 and 50
        p.mass = static_cast<float>(rand()) / RAND_MAX * 10.0f; // Random mass between 0 and 10
        p.posX = static_cast<float>(rand()) / RAND_MAX * 100.0f; // Random position X between 0 and 100
        p.posY = static_cast<float>(rand()) / RAND_MAX * 100.0f; // Random position Y between 0 and 100
        particles.push_back(p);
    }



    for (uint8_t i = 0; i < 100; ++i)
    {
        float accX = 0.0f;
        float accY = 0.0f;
        for (uint8_t j = 0; j < 100; ++j)
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

            float acc = G * particleB.mass / (distanceSquared + 1e-10f); // Add small value to prevent division by zero

            accX += acc * (dx / distance);

            accY += acc * (dy / distance);

        }

        particles[i].accX += accX;
        particles[i].accY += accY;
    }

    for (auto& particle : particles)
    {
        particle.velocityX += particle.accX * TIME_STEP;
        particle.velocityY += particle.accY * TIME_STEP;
        particle.posX += particle.velocityX * TIME_STEP;
        particle.posY += particle.velocityY * TIME_STEP;
    }
}