#include <iostream>
#include <vector>
#include "node.hpp"
#include <algorithm>
#include "timer.hpp"
#include <ctime>
#include <omp.h>
#include <fstream> 
#include <cmath>
#include <iomanip>

constexpr float G = 1.0f;
constexpr float TIME_STEP = 0.016f;
constexpr float THETA = 0.3f;
constexpr float FRAMES = 10;
constexpr int NUM_PARTICLES = 5000000;
std::string inputFile = "start_5000k.txt";

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
        float shift = 0.0001f;
        while (particles[pIdx].posX == particles[oldIdx].posX && particles[pIdx].posY == particles[oldIdx].posY) 
        {
            particles[pIdx].posX += shift;
            shift *= 2.0f;
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

        if (distSq < 1e-5f) 
        {
            currNodeIdx = node.next;
            continue;
        }

        float side_length = node.halfSize * 2.0f;
        // if ((s / dist) < THETA 
        float r_c_sq = (side_length * side_length) * 0.5; // (s_c * sqrt(2)/2)^2 = s_c^2 * 0.5
        if (r_c_sq < THETA * THETA * distSq || node.children[0] == -1)
        {
            float dist = std::sqrt(distSq);
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

void validateForceAccuracy(int currentFrame, const std::vector<Particle>& bh_particles)
{
    std::cout << "\n--- WALIDACJA DOKLADNOSCI SILY (Klatka " << currentFrame << ") ---\n";

    double sum_diff_sq = 0.0;
    double sum_bf_sq = 0.0;
    std::vector<double> local_relative_errors;
    local_relative_errors.reserve(bh_particles.size());

    // Obliczamy referencyjne siły O(N^2) na aktualnych pozycjach Barnes-Hut
    #pragma omp parallel for reduction(+:sum_diff_sq, sum_bf_sq) schedule(dynamic, 32)
    for (int i = 0; i < bh_particles.size(); ++i) 
    {
        float exact_accX = 0.0f;
        float exact_accY = 0.0f;
        
        for (int j = 0; j < bh_particles.size(); ++j) 
        {
            if (i == j) continue;
            float dx = bh_particles[j].posX - bh_particles[i].posX;
            float dy = bh_particles[j].posY - bh_particles[i].posY;
            float distSq = dx * dx + dy * dy;
            
            if (distSq < 1e-5f) continue;
            
            float dist = std::sqrt(distSq);
            float acc = G * bh_particles[j].mass / (distSq + 1.0f);
            exact_accX += acc * (dx / dist);
            exact_accY += acc * (dy / dist);
        }

        double diffX = bh_particles[i].accX - exact_accX;
        double diffY = bh_particles[i].accY - exact_accY;
        
        double diff_sq = diffX * diffX + diffY * diffY;
        double bf_sq = exact_accX * exact_accX + exact_accY * exact_accY;
        
        sum_diff_sq += diff_sq;
        sum_bf_sq += bf_sq;

        // Błąd względny dla 95 percentyla
        double exact_norm = std::sqrt(bf_sq);
        double diff_norm = std::sqrt(diff_sq);
        if (exact_norm > 1e-6) {
            double rel_err = diff_norm / exact_norm;
            #pragma omp critical
            {
                local_relative_errors.push_back(rel_err);
            }
        }
    }

    double rms_error = std::sqrt(sum_diff_sq / sum_bf_sq);
    
    std::sort(local_relative_errors.begin(), local_relative_errors.end());
    double p95_error = 0.0;
    if (!local_relative_errors.empty()) {
        size_t p95_index = static_cast<size_t>(0.95 * local_relative_errors.size());
        p95_error = local_relative_errors[p95_index];
    }

    std::cout << std::fixed << std::setprecision(4);
    std::cout << "Globalny blad sily (RMS): " << rms_error * 100.0 << " %\n";
    std::cout << "Blad 95. percentyla:      " << p95_error * 100.0 << " %\n";
    std::cout << "--------------------------------------------------\n";
}

int mainMain()
{
    omp_set_num_threads(12);
    srand(42);
    std::vector<Particle> particles;
    std::vector<Node> treeArena;
    Timer timer;
    float totalTreeBuildTime = 0.0f;
    float totalForceTime = 0.0f;
    unsigned long long totalCyclesTree = 0;
    unsigned long long totalCyclesForce = 0;

    std::ifstream inFile(inputFile);
    if (!inFile)
    {
        std::cerr << "Blad: Nie mozna otworzyc pliku " << inputFile << "!\n";
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
        // if (frame == 0) {
        //     // Rozmiar cząstek:
        //     size_t particlesMem = particles.capacity() * sizeof(Particle);
        //     // Maksymalny rozmiar zarezerwowanej areny drzewa:
        //     size_t treeMem = treeArena.capacity() * sizeof(Node); 
            
        //     double totalAppMemMB = static_cast<double>(particlesMem + treeMem) / (1024.0 * 1024.0);
        //     std::cout << std::fixed << std::setprecision(6);
        //     std::cout << "Zuzycie pamieci algorytmu: " << totalAppMemMB << " MB\n";
        //     std::cout << "Stworzono " << treeArena.size() << " wezlow drzewa.\n";
        //     std::cout << "Size of Particle: " << sizeof(Particle) << " bytes\n";
        //     std::cout << "Size of Node (V4/V5): " << sizeof(Node) << " bytes\n";
        // }

        computeMassDistribution(0, treeArena, particles);
        threadTree(0, -1, treeArena);
        totalTreeBuildTime += timer.stopTime();
        totalCyclesTree += timer.stopCycles();

        timer.start();
        #pragma omp parallel for schedule(dynamic, 32)
        for (int i = 0; i < particles.size(); ++i)
        {
            calculateForces(i, particles, treeArena);
        }

        // if (frame == FRAMES - 1) {
        //     validateForceAccuracy(frame, particles);
        // }

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
        totalForceTime += timer.stopTime();
        totalCyclesForce += timer.stopCycles();
        // if (frame % 25 == 0 or frame == FRAMES - 1) {
        //     auto metrics = calculatePhysicsDiagnostics(particles);
        //     std::cout << "Frame " << frame << ":\n";
        //     std::cout << "Ped (" << metrics.totalMomentumX << ", " << metrics.totalMomentumY << ")\n";
        //     std::cout << "Energia kinetyczna " << metrics.totalKineticEnergy << "\n";
        //     std::cout << "Srodek masy (" << metrics.centerX << ", " << metrics.centerY << ")\n";
        // }
    }
    std::cout << "Czas budowy drzewa: " << (totalTreeBuildTime / FRAMES) << " ms / klatke\n";
    std::cout << "Czas liczenia sil:  " << (totalForceTime / FRAMES) << " ms / klatke\n";
    std::cout << "Calkowity czas symulacji: " << (totalTreeBuildTime + totalForceTime) << " ms\n";
    std::cout << "Cykle budowy drzewa: " << std::fixed << (totalCyclesTree / FRAMES) << " cykli / klatke\n";
    std::cout << "Cykle liczenia sil:  " << std::fixed << (totalCyclesForce / FRAMES) << " cykli / klatke\n";
    // std::ifstream outFile("wzorzec_5000k.txt");
    // if (!outFile) 
    // {
    //     std::cout << "file error.\n";
    // } 
    // else 
    // {
    //     float totalError = 0.0f;
    //     float maxError = 0.0f;
    //     float refX = 0.0f, refY = 0.0f;
        
    //     for (const auto& p : particles)
    //     {
    //         outFile >> refX >> refY;
            
    //         float dx = p.posX - refX;
    //         float dy = p.posY - refY;
    //         float currentError = std::sqrt(dx * dx + dy * dy);
    //         totalError += currentError;
    //         if (currentError > maxError) {
    //             maxError = currentError; 
    //         }
    //     }
    //     outFile.close();
        
    //     float meanAbsoluteError = totalError / NUM_PARTICLES;
    //     std::cout << "Sredni blad pozycji (MAE): " << meanAbsoluteError << " jednostek\n";
    //     std::cout << "Maksymalny blad pozycji: " << maxError << " jednostek\n";
    // }
    return 0;
}

int main() {
    
    for (int i = 0; i < 3; ++i) {
        mainMain();
    }
    return 0;
}