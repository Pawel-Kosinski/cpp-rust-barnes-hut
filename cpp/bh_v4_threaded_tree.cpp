#include <iostream>
#include <vector>
#include "node.hpp"
#include <algorithm>
#include "timer.hpp"
#include <ctime>
#include <fstream> 
#include <cmath>
#include <iomanip>
#include "benchmark_options.hpp"

constexpr float G = 1.0f;
constexpr float TIME_STEP = 0.016f;
float THETA = 0.3f;
using Node = NodeV4;

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
        arena[nodeIdx].children[i] = static_cast<int>(arena.size());
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
        float r_c_sq = (side_length * side_length) * 0.5f; // (s_c * sqrt(2)/2)^2 = s_c^2 * 0.5
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

// struct PhysicsMetrics {
//     double totalMomentumX = 0.0;
//     double totalMomentumY = 0.0;
//     double totalKineticEnergy = 0.0;
//     double centerX = 0.0;
//     double centerY = 0.0;
// };

// PhysicsMetrics calculatePhysicsDiagnostics(const std::vector<Particle>& particles) {
//     PhysicsMetrics m;
//     double totalMass = 0.0;

//     for (const auto& p : particles) {
//         double mass = static_cast<double>(p.mass);
//         double vx = static_cast<double>(p.velocityX);
//         double vy = static_cast<double>(p.velocityY);
//         double px = static_cast<double>(p.posX);
//         double py = static_cast<double>(p.posY);

//         m.totalMomentumX += mass * vx;
//         m.totalMomentumY += mass * vy;
//         m.totalKineticEnergy += 0.5 * mass * (vx * vx + vy * vy);

//         m.centerX += mass * px;
//         m.centerY += mass * py;
//         totalMass += mass;
//     }

//     m.centerX /= totalMass;
//     m.centerY /= totalMass;

//     return m;
// }

void validateForceAccuracy(int currentFrame, const std::vector<Particle>& bh_particles)
{
    std::cout << "\n--- FORCE ACCURACY VALIDATION (Frame " << currentFrame << ") ---\n";

    double sum_diff_sq = 0.0;
    double sum_bf_sq = 0.0;
    std::vector<double> local_relative_errors;
    local_relative_errors.reserve(bh_particles.size());

    // Compute reference O(N^2) forces for the current Barnes-Hut positions
    //#pragma omp parallel for reduction(+:sum_diff_sq, sum_bf_sq) schedule(dynamic, 32)
    for (std::size_t i = 0; i < bh_particles.size(); ++i)
    {
        float exact_accX = 0.0f;
        float exact_accY = 0.0f;
        
        for (std::size_t j = 0; j < bh_particles.size(); ++j)
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

        // Relative error for the 95th percentile
        double exact_norm = std::sqrt(bf_sq);
        double diff_norm = std::sqrt(diff_sq);
        if (exact_norm > 1e-6) {
            double rel_err = diff_norm / exact_norm;
            local_relative_errors.push_back(rel_err);
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
    std::cout << "Global force error (RMS): " << rms_error * 100.0 << " %\n";
    std::cout << "95th percentile error:      " << p95_error * 100.0 << " %\n";
    std::cout << "--------------------------------------------------\n";
}

int mainMain(const BenchmarkOptions& options)
{
    srand(42);
    std::vector<Particle> particles;
    std::vector<Node> treeArena;
    //treeArena.reserve(particles.size() * 6);
    Timer timer;
    double totalTreeBuildTime = 0.0;
    double totalForceTime = 0.0;

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

    //treeArena.reserve(particles.size() * 6);

    for (int frame = 0; frame < options.totalFrames(); ++frame)
    {
        timer.start(); 
        float minX = particles[0].posX, maxX = particles[0].posX;
        float minY = particles[0].posY, maxY = particles[0].posY;
        
        for (const auto& particle : particles)
        {
            if (particle.posX < minX) minX = particle.posX;
            if (particle.posX > maxX) maxX = particle.posX;
            if (particle.posY < minY) minY = particle.posY;
            if (particle.posY > maxY) maxY = particle.posY;
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

        for (std::size_t i = 0; i < particles.size(); ++i)
        {
            insertParticle(0, static_cast<int>(i), treeArena, particles);
        }
        // if (frame == 0) {
        //     // Particle array size:
        //     size_t particlesMem = particles.capacity() * sizeof(Particle);
        //     // Maximum reserved tree-arena size:
        //     size_t treeMem = treeArena.capacity() * sizeof(Node);

        //     std::cout << std::fixed << std::setprecision(6);
        //     double totalAppMemMB = static_cast<double>(particlesMem + treeMem) / (1024.0 * 1024.0);
        //     std::cout << "Algorithm memory usage: " << totalAppMemMB << " MB\n";
        //     std::cout << "Created " << treeArena.size() << " tree nodes.\n";
        //     std::cout << "Size of Particle: " << sizeof(Particle) << " bytes\n";
        //     std::cout << "Size of Node (V4/V5): " << sizeof(Node) << " bytes\n";
        // }

        computeMassDistribution(0, treeArena, particles);
        threadTree(0, -1, treeArena);

        const double treeTime = timer.stopTime();
        if (frame >= options.warmupFrames) totalTreeBuildTime += treeTime;
        // if(frame == 0) {
        //     std::cout << "Tree construction time: " << (totalTreeBuildTime) << " ms\n";
        //     std::cout << "Tree construction cycles: " << std::fixed << (totalCyclesTree) << " cycles\n";
        // }

        timer.start();
        for (std::size_t i = 0; i < particles.size(); ++i)
        {
            calculateForces(static_cast<int>(i), particles, treeArena);
        }

        if (frame == options.warmupFrames && !writeForces(options.dumpForces, particles)) return 1;

        // if (frame == 0 or frame == FRAMES - 1 or frame == 150) { 
        //     validateForceAccuracy(frame, particles);
        // }
        // ---------------------------------------------------------

        // POSITION UPDATE AND FORCE RESET
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
        // if (frame == 0 or frame == FRAMES - 1) {
        //     auto metrics = calculatePhysicsDiagnostics(particles);
        //     std::cout << "Frame " << frame << ":\n";
        //     std::cout << "Ped (" << metrics.totalMomentumX << ", " << metrics.totalMomentumY << ")\n";
        //     std::cout << "Energia kinetyczna " << metrics.totalKineticEnergy << "\n";
        //     std::cout << "Srodek masy (" << metrics.centerX << ", " << metrics.centerY << ")\n";
        // }
    }

    std::cout << std::fixed << std::setprecision(6);
    std::cout << "Tree construction time: " << (totalTreeBuildTime / options.frames) << " ms / frame\n";
    std::cout << "Force/update time: " << (totalForceTime / options.frames) << " ms / frame\n";
    std::cout << "Cleanup time: 0.000000 ms / frame\n";
    std::cout << "Total measured time: " << (totalTreeBuildTime + totalForceTime) << " ms\n";
    // std::ifstream outFile("reference_5000k.txt");
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
    //     std::cout << "Mean absolute position error (MAE): " << meanAbsoluteError << " units\n";
    //     std::cout << "Maximum position error: " << maxError << " units\n";
    // }
    return 0;
}

int main(int argc, char** argv)
{
    BenchmarkOptions options;
    if (!parseBenchmarkOptions(argc, argv, options)) return argc > 1 ? 1 : 0;
    THETA = options.theta;
    return mainMain(options);
}
