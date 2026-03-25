#include <vector>
#include <cmath>
#include "timer.hpp"
#include <iostream>
#include <fstream> 
#include <cmath>

constexpr float G = 1.0f;
constexpr float TIME_STEP = 0.016f;
constexpr float THETA = 0.5f;
constexpr float FRAMES = 300;
constexpr int NUM_PARTICLES = 10000;

struct NodePtr 
{
    float boundsX{0.0f}, boundsY{0.0f}, halfSize{0.0f};
    float mass{0.0f}, centerX{0.0f}, centerY{0.0f};
    int particleIndex{-1};
    NodePtr* children[4]{nullptr, nullptr, nullptr, nullptr};
};

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

int getQuadrantPtr(const NodePtr* node, const Particle& particle) 
{
    int index = 0;
    if (particle.posX > node->boundsX) index += 1;
    if (particle.posY > node->boundsY) index += 2;
    return index;
}

//Budowa drzewa 
void insertParticlePtr(NodePtr* node, int pIdx, std::vector<Particle>& particles) 
{
    if (node->particleIndex != -1) 
    {
        int oldIdx = node->particleIndex;
        if (particles[pIdx].posX == particles[oldIdx].posX && particles[pIdx].posY == particles[oldIdx].posY) 
            particles[pIdx].posX += 0.0001f;
    }

    if (node->children[0] != nullptr) 
    {
        int quad = getQuadrantPtr(node, particles[pIdx]);
        insertParticlePtr(node->children[quad], pIdx, particles);
        return;
    }

    if (node->particleIndex == -1) 
    {
        node->particleIndex = pIdx;
        return;
    }

    int oldPIdx = node->particleIndex;
    node->particleIndex = -1;
    float hSize = node->halfSize / 2.0f;

    for (int i = 0; i < 4; ++i) 
    {
        node->children[i] = new NodePtr(); //Alokacja na stercie
        node->children[i]->halfSize = hSize;
        node->children[i]->boundsX = node->boundsX + ((i % 2) * 2 - 1) * hSize;
        node->children[i]->boundsY = node->boundsY + ((i / 2) * 2 - 1) * hSize;
    }

    insertParticlePtr(node, oldPIdx, particles);
    insertParticlePtr(node, pIdx, particles);
}

// Obliczanie Środka Masy (Rekurencja od dołu do góry)
void computeMassDistributionPtr(NodePtr* node, const std::vector<Particle>& particles) 
{
    if (node->children[0] != nullptr) 
    {
        node->mass = 0.0f;
        node->centerX = 0.0f;
        node->centerY = 0.0f;

        for (int i = 0; i < 4; ++i) 
        {
            computeMassDistributionPtr(node->children[i], particles);
            float childMass = node->children[i]->mass;
            node->mass += childMass;
            node->centerX += node->children[i]->centerX * childMass;
            node->centerY += node->children[i]->centerY * childMass;
        }

        if (node->mass > 0.0f) 
        {
            node->centerX /= node->mass;
            node->centerY /= node->mass;
        }
    } 
    else if (node->particleIndex != -1) 
    {
        const Particle& p = particles[node->particleIndex];
        node->mass = p.mass;
        node->centerX = p.posX;
        node->centerY = p.posY;
    }
}

// Obliczanie Sił (Rekurencja top-down)
void calculateForcesPtr(int pIdx, NodePtr* node, std::vector<Particle>& particles) 
{
    if (node == nullptr) return;

    Particle& p = particles[pIdx];
    float dx = node->centerX - p.posX;
    float dy = node->centerY - p.posY;
    float distSq = dx * dx + dy * dy;

    if (distSq < 1e-5f) return;

    float dist = std::sqrt(distSq);
    float s = node->halfSize * 2.0f;

    if ((s / dist) < THETA || node->children[0] == nullptr) 
    {
        float acc = G * node->mass / (distSq + 1.0f);
        p.accX += acc * (dx / dist);
        p.accY += acc * (dy / dist);
    } 
    else 
    {
        for (int i = 0; i < 4; ++i) 
        {
            calculateForcesPtr(pIdx, node->children[i], particles);
        }
    }
}

void deleteTreePtr(NodePtr* node) 
{
    if (node == nullptr) return;
    for (int i = 0; i < 4; ++i) 
    {
        deleteTreePtr(node->children[i]);
    }
    delete node; 
}

int main()
{
    srand(42);
    std::vector<Particle> particles;
    Timer timer;
    float totalTreeBuildTime = 0.0f;
    float totalForceTime = 0.0f;
    unsigned long long totalCyclesTree = 0;
    unsigned long long totalCyclesForce = 0;

    for (int i = 0; i < NUM_PARTICLES; ++i)
    {
        Particle p;
        p.velocityX = (static_cast<float>(rand()) / RAND_MAX * 50.0f) - 25.0f;
        p.velocityY = (static_cast<float>(rand()) / RAND_MAX * 50.0f) - 25.0f;
        p.mass = static_cast<float>(rand()) / RAND_MAX * 10.0f;
        p.posX = static_cast<float>(rand()) / RAND_MAX * 100.0f;
        p.posY = static_cast<float>(rand()) / RAND_MAX * 100.0f;
        particles.push_back(p);
    }


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

        NodePtr* rootPtr = new NodePtr();
        rootPtr->boundsX = centerX;
        rootPtr->boundsY = centerY;
        rootPtr->halfSize = maxHalfSize;

        for (int i = 0; i < particles.size(); ++i) {
            insertParticlePtr(rootPtr, i, particles);
        }

        computeMassDistributionPtr(rootPtr, particles);
        totalTreeBuildTime += timer.stopTime();
        totalCyclesTree += timer.stopCycles();

        timer.start();
        for (int i = 0; i < particles.size(); ++i)
        {
            calculateForcesPtr(i, rootPtr, particles);
        }
        deleteTreePtr(rootPtr);
        totalForceTime += timer.stopTime();
        totalCyclesForce += timer.stopCycles();

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
    std::cout << "WYNIKI WYDAJNOSCIOWE (Srednia z wszystkich klatek) \n";
    std::cout << " | Korzen Masy: X=" << particles[0].posX << " Y=" << particles[0].posY << std::endl;
    std::cout << "Czas budowy drzewa: " << (totalTreeBuildTime / FRAMES) << " ms / klatke\n";
    std::cout << "Czas liczenia sil:  " << (totalForceTime / FRAMES) << " ms / klatke\n";
    std::cout << "Calkowity czas symulacji: " << (totalTreeBuildTime + totalForceTime) << " ms\n";
    std::cout << "Cykle budowy drzewa: " << std::fixed << (totalCyclesTree / FRAMES) << " cykli / klatke\n";
    std::cout << "Cykle liczenia sil:  " << std::fixed << (totalCyclesForce / FRAMES) << " cykli / klatke\n";
    std::ifstream inFile("wzorzec_10k.txt");
    if (!inFile) 
    {
        std::cout << "file error.\n";
    } 
    else 
    {
        float totalError = 0.0f;
        float refX = 0.0f, refY = 0.0f;
        
        for (const auto& p : particles)
        {
            inFile >> refX >> refY;
            
            float dx = p.posX - refX;
            float dy = p.posY - refY;
            totalError += std::sqrt(dx * dx + dy * dy);
        }
        inFile.close();
        
        float meanAbsoluteError = totalError / NUM_PARTICLES;
        std::cout << "Sredni blad pozycji (MAE): " << meanAbsoluteError << " jednostek\n";
    }
    return 0;
}