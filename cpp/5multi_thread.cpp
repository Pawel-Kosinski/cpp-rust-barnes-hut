#include <iostream>
#include <vector>
#include "node.hpp"
#include <algorithm>
#include "timer.hpp"
#include <ctime>
#include <omp.h>
#include <fstream> 
#include <cmath>

constexpr float G = 1.0f;
constexpr float TIME_STEP = 0.016f;
constexpr float THETA = 0.4;
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

void calculateForces(int pIdx, std::vector<Particle>& particles, const std::vector<Node>& arena)
{
    Particle& p = particles[pIdx];
    int currNodeIdx = 0; 

    while (currNodeIdx != -1)
    {
        const Node& node = arena[currNodeIdx];

        float dx = node.centerX - p.posX;
        float dy = node.centerY - p.posY;
        float distSq = dx * dx + dy * dy;
        float dist = std::sqrt(distSq);

        if (distSq < 1e-5f) 
        {
            currNodeIdx = node.next;
            continue;
        }

        float s = node.halfSize * 2.0f;
        if ((s / dist) < THETA || node.children[0] == -1)
        {
            float acc = G * node.mass / (distSq + 1.0f);
            p.accX += acc * (dx / dist);
            p.accY += acc * (dy / dist);

            currNodeIdx = node.next;
        }
        else
        {
            currNodeIdx = node.children[0];
        }
    }
}

float mainLoop(std::vector<Particle> particles)
{
    std::vector<Node> treeArena;
    Timer timer;
    float totalTreeBuildTime = 0.0f;
    float totalForceTime = 0.0f;
    unsigned long long totalCyclesTree = 0;
    unsigned long long totalCyclesForce = 0;
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
        if (frame == 0) {
            // Rozmiar cząstek:
            size_t particlesMem = particles.capacity() * sizeof(Particle);
            // Maksymalny rozmiar zarezerwowanej areny drzewa:
            size_t treeMem = treeArena.capacity() * sizeof(Node); 
            
            double totalAppMemMB = static_cast<double>(particlesMem + treeMem) / (1024.0 * 1024.0);
            std::cout << "Prawdziwe zuzycie pamieci algorytmu: " << totalAppMemMB << " MB\n";
            std::cout << "Stworzono " << treeArena.size() << " wezlow drzewa.\n";
        }

        computeMassDistribution(0, treeArena, particles);
        threadTree(0, -1, treeArena);
        totalTreeBuildTime += timer.stopTime();
        totalCyclesTree += timer.stopCycles();

        timer.start();
        #pragma omp parallel for
        for (int i = 0; i < particles.size(); ++i)
        {
            calculateForces(i, particles, treeArena);
        }
        totalForceTime += timer.stopTime();
        totalCyclesForce += timer.stopCycles();

        #pragma omp parallel for
        for (int i = 0; i < particles.size(); ++i)
        {
            Particle& particle = particles[i];
        
            particle.velocityX += particle.accX * TIME_STEP;
            particle.velocityY += particle.accY * TIME_STEP;
            particle.posX += particle.velocityX * TIME_STEP;
            particle.posY += particle.velocityY * TIME_STEP;
            
            particle.accX = 0.0f; 
            particle.accY = 0.0f; 
        }
    }
    std::cout << " | Korzen Masy: X=" << particles[0].posX << " Y=" << particles[0].posY << std::endl;
    std::cout << "WYNIKI WYDAJNOSCIOWE (Srednia z wszystkich klatek) \n";
    std::cout << "Czas budowy drzewa: " << (totalTreeBuildTime / FRAMES) << " ms / klatke\n";
    std::cout << "Czas liczenia sil:  " << (totalForceTime / FRAMES) << " ms / klatke\n";
    std::cout << "Calkowity czas symulacji: " << (totalTreeBuildTime + totalForceTime) << " ms\n";
    std::cout << "Cykle budowy drzewa: " << std::fixed << (totalCyclesTree / FRAMES) << " cykli / klatke\n";
    std::cout << "Cykle liczenia sil:  " << std::fixed << (totalCyclesForce / FRAMES) << " cykli / klatke\n";
    std::ifstream outFile("wzorzec_10k.txt");
    if (!outFile) 
    {
        std::cout << "file error.\n";
    } 
    else 
    {
        float totalError = 0.0f;
        float maxError = 0.0f;
        float refX = 0.0f, refY = 0.0f;
        
        for (const auto& p : particles)
        {
            outFile >> refX >> refY;
            
            float dx = p.posX - refX;
            float dy = p.posY - refY;
            float currentError = std::sqrt(dx * dx + dy * dy);
            totalError += currentError;
            if (currentError > maxError) {
                maxError = currentError; 
            }
        }
        outFile.close();
        
        float meanAbsoluteError = totalError / NUM_PARTICLES;
        std::cout << "Sredni blad pozycji (MAE): " << meanAbsoluteError << " jednostek\n";
        std::cout << "Maksymalny blad pozycji: " << maxError << " jednostek\n";
    }
    return totalForceTime / FRAMES;
}
int main()
{
    srand(42);
    std::vector<Particle> particles;


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
    //std::vector<Particle> originalParticles = particles;
    std::vector<int> threadCounts = {1, 2, 4, 8, 16, 32}; 
    std::vector<double> forceTimes(threadCounts.size());

    for(size_t t = 0; t < threadCounts.size(); ++t)
    {
        int numThreads = threadCounts[t];
        omp_set_num_threads(numThreads);
        //particles = originalParticles;
        std::cout << "Watki: " << numThreads << std::endl;
        forceTimes[t] = mainLoop(particles);
    }

    std::cout << "\nWYNIKI SKALOWANIA\n";
    double timeSeq = forceTimes[0];
    for(size_t t = 0; t < threadCounts.size(); ++t)
    {
        int p = threadCounts[t];
        double timeP = forceTimes[t];
        
        double speedup = timeSeq / timeP;          // S_p = T_1 / T_p
        double efficiency = speedup / p;           // E_p = S_p / p
        
        std::cout << "Watki (p): " << p 
                  << " | Czas (T_p): " << timeP << " ms"
                  << " | Speedup (S_p): " << speedup 
                  << " | Efficiency (E_p): " << (efficiency * 100.0) << " %\n";
    }

    return 0;
}