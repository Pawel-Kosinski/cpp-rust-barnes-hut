#include <iostream>
#include <vector>
#include "node.hpp"
#include <algorithm>
#include "timer.hpp"

constexpr float G = 1.0f; // Gravitational constant
constexpr float TIME_STEP = 0.016f; // Time step for the simulation
constexpr float THETA = 0.5f;
constexpr float FRAMES = 1000;

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

int getQuadrant(const Node& node, const Particle& particle) 
{
    int index = 0; 

    if (particle.posX > node.boundsX) 
    {
        index += 1; 
    }

    if (particle.posY > node.boundsY) 
    {
        index += 2; 
    }

    return index;
}
void insertParticle(int nodeIdx, int pIdx, std::vector<Node>& arena, std::vector<Particle>& particles)
{
    if (arena[nodeIdx].particleIndex != -1) 
    {
        int oldIdx = arena[nodeIdx].particleIndex;
        if (particles[pIdx].posX == particles[oldIdx].posX && 
            particles[pIdx].posY == particles[oldIdx].posY) 
        {
            particles[pIdx].posX += 0.0001f;
        }
    }

    if (arena[nodeIdx].particleIndex == -1 && arena[nodeIdx].children[0] == -1)
    {
        arena[nodeIdx].particleIndex = pIdx;
        return;
    }
    if (arena[nodeIdx].children[0] != -1)
    {
        int quadrant = getQuadrant(arena[nodeIdx], particles[pIdx]);
        insertParticle(arena[nodeIdx].children[quadrant], pIdx, arena, particles);
        return;
    }

    int oldPIdx = arena[nodeIdx].particleIndex;
    arena[nodeIdx].particleIndex = -1;
    for (int i = 0; i < 4; ++i)
    {
        Node child;
        child.halfSize = arena[nodeIdx].halfSize / 2.0f;
        child.boundsX = arena[nodeIdx].boundsX + ((i % 2) * 2 - 1) * child.halfSize;
        child.boundsY = arena[nodeIdx].boundsY + ((i / 2) * 2 - 1) * child.halfSize;
        arena[nodeIdx].children[i] = arena.size();
        arena.push_back(child);
    }
    insertParticle(nodeIdx, oldPIdx, arena, particles);
    insertParticle(nodeIdx, pIdx, arena, particles);
}

void computeMassDistribution(int nodeIdx, std::vector<Node>& arena, const std::vector<Particle>& particles)
{
    Node& node = arena[nodeIdx];
    if (node.children[0] != -1)
    {
        node.mass = 0.0f;
        node.centerX = 0.0f;
        node.centerY = 0.0f;
        for (int i = 0; i < 4; ++i)
        {
            int childIdx = node.children[i];
            computeMassDistribution(childIdx, arena, particles);
            float childMass = arena[childIdx].mass;
            node.mass += childMass;

            node.centerX += arena[childIdx].centerX * childMass;
            node.centerY += arena[childIdx].centerY * childMass;
        }
        if (node.mass > 0.0f)
        {
            node.centerX /= node.mass;
            node.centerY /= node.mass;
        }
    }

    else if(node.particleIndex != -1)
    {
        const Particle& p = particles[node.particleIndex];
        node.mass = p.mass;
        node.centerX = p.posX;
        node.centerY = p.posY;
    }
    else 
    {
        node.mass = 0.0f;
        node.centerX = 0.0f;
        node.centerY = 0.0f;
    }
}

void threadTree(int nodeIdx, int nextIdx, std::vector<Node>& arena)
{
    arena[nodeIdx].next = nextIdx;
    if (arena[nodeIdx].children[0] != -1)
    {
        for (int i = 0; i < 3; ++i)
        {
            threadTree(arena[nodeIdx].children[i], arena[nodeIdx].children[i + 1], arena);
        }
        threadTree(arena[nodeIdx].children[3], nextIdx, arena);
    }
}

void calculateForcesRecursive(int pIdx, int nodeIdx, std::vector<Particle>& particles, const std::vector<Node>& arena)
{
    // Zabezpieczenie przed pustymi dziećmi
    if (nodeIdx == -1) return;

    Particle& p = particles[pIdx];
    const Node& node = arena[nodeIdx];

    float dx = node.centerX - p.posX;
    float dy = node.centerY - p.posY;
    float distSq = dx * dx + dy * dy;

    // Nie przyciągamy się sami do siebie
    if (distSq < 1e-5f) return;

    float dist = std::sqrt(distSq);
    float s = node.halfSize * 2.0f;

    // KRYTERIUM AKCEPTACJI: Daleko lub Liść
    if ((s / dist) < THETA || node.children[0] == -1)
    {
        float acc = G * node.mass / (distSq + 1e-10f);
        p.accX += acc * (dx / dist);
        p.accY += acc * (dy / dist);
    }
    else
    {
        // WĘZEŁ ZA BLISKO - Schodzimy w dół rekurencyjnie (Brak użycia 'next')
        for (int i = 0; i < 4; ++i)
        {
            if (node.children[i] != -1)
            {
                calculateForcesRecursive(pIdx, node.children[i], particles, arena);
            }
        }
    }
}

int main()
{
    std::vector<Particle> particles;
    std::vector<Node> treeArena;
    Timer timer;
    float totalTreeBuildTime = 0.0f;
    float totalForceTime = 0.0f;

    // Generowanie cząstek
    for (int i = 0; i < 400; ++i)
    {
        Particle p;
        p.velocityX = (static_cast<float>(rand()) / RAND_MAX * 50.0f) - 25.0f;
        p.velocityY = (static_cast<float>(rand()) / RAND_MAX * 50.0f) - 25.0f;
        p.mass = static_cast<float>(rand()) / RAND_MAX * 10.0f;
        p.posX = static_cast<float>(rand()) / RAND_MAX * 100.0f;
        p.posY = static_cast<float>(rand()) / RAND_MAX * 100.0f;
        particles.push_back(p);
    }

    treeArena.reserve(particles.size() * 10);

    // Pętla symulacji
    for (int frame = 0; frame < FRAMES; ++frame)
    {
        timer.start(); 
        float minX = particles[0].posX, maxX = particles[0].posX;
        float minY = particles[0].posY, maxY = particles[0].posY;
        
        for (const auto& p : particles)
        {
            if (p.posX < minX) minX = p.posX;
            if (p.posX > maxX) maxX = p.posX;
            if (p.posY < minY) minY = p.posY;
            if (p.posY > maxY) maxY = p.posY;
        }

        float centerX = (minX + maxX) / 2.0f;
        float centerY = (minY + maxY) / 2.0f;
        float halfWidth = (maxX - minX) / 2.0f;
        float halfHeight = (maxY - minY) / 2.0f;
        float maxHalfSize = std::max(halfWidth, halfHeight) + 1.0f;

        treeArena.clear();
        Node root; 
        root.boundsX = centerX; 
        root.boundsY = centerY; 
        root.halfSize = maxHalfSize;
        treeArena.push_back(root);

        for (int i = 0; i < particles.size(); ++i)
        {
            insertParticle(0, i, treeArena, particles);
        }

        computeMassDistribution(0, treeArena, particles);
        threadTree(0, -1, treeArena);
        totalTreeBuildTime += timer.stop();

        timer.start();
        for (int i = 0; i < particles.size(); ++i)
        {
            calculateForcesRecursive(i, 0, particles, treeArena);
        }
        totalForceTime += timer.stop();

        for (auto& particle : particles)
        {
            particle.velocityX += particle.accX * TIME_STEP;
            particle.velocityY += particle.accY * TIME_STEP;
            particle.posX += particle.velocityX * TIME_STEP;
            particle.posY += particle.velocityY * TIME_STEP;
            
            particle.accX = 0.0f; 
            particle.accY = 0.0f; 
        }
        
        std::cout << "Klatka " << frame << " | Korzen Masy: X=" 
                  << treeArena[0].centerX << ", Y=" << treeArena[0].centerY << "\n";
    }
    std::cout << "WYNIKI WYDAJNOSCIOWE (Srednia z wszystkich klatek) \n";
    std::cout << "Czas budowy drzewa: " << (totalTreeBuildTime / FRAMES) << " ms / klatke\n";
    std::cout << "Czas liczenia sil:  " << (totalForceTime / FRAMES) << " ms / klatke\n";
    std::cout << "Calkowity czas symulacji: " << (totalTreeBuildTime + totalForceTime) << " ms\n";
    return 0;
}