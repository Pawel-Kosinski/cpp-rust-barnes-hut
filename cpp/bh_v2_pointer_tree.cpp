#include <vector>
#include <cmath>
#include "timer.hpp"
#include <iostream>
#include <fstream>
#include <cmath>
#include <iomanip>
#include "benchmark_options.hpp"

constexpr float G = 1.0f;
constexpr float TIME_STEP = 0.016f;
float THETA = 0.3f;

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

//Tree construction
void insertParticlePtr(NodePtr* node, int pIdx, std::vector<Particle>& particles)
{
    if (node->particleIndex != -1)
    {
        int oldIdx = node->particleIndex;
        float shift = 0.0001f;
        while (particles[pIdx].posX == particles[oldIdx].posX && particles[pIdx].posY == particles[oldIdx].posY)
        {
            particles[pIdx].posX += shift;
            shift *= 2.0f;
        }
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

// Center-of-mass computation (bottom-up recursion)
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

// Force computation (top-down recursion)
void calculateForcesPtr(int pIdx, NodePtr* node, std::vector<Particle>& particles)
{
    if (node == nullptr) return;

    Particle& p = particles[pIdx];
    float dx = node->centerX - p.posX;
    float dy = node->centerY - p.posY;
    float distSq = dx * dx + dy * dy;

    if (distSq < 1e-5f) return;

    float side_length = node->halfSize * 2.0f;
    // if ((s / dist) < THETA
    float r_c_sq = (side_length * side_length) * 0.5f; // (s_c * sqrt(2)/2)^2 = s_c^2 * 0.5
    if (r_c_sq < THETA * THETA * distSq || node->children[0] == nullptr)
    {
        float dist = std::sqrt(distSq);
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

int countNodesPtr(NodePtr* node)
{
    int count = 1;
    for (int i = 0; i < 4; ++i)
    {
        if (node->children[i] != nullptr)
        {
            count += countNodesPtr(node->children[i]);
        }
    }
    return count;
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

int mainMain(const BenchmarkOptions& options)
{
    srand(42);
    std::vector<Particle> particles;
    Timer timer;
    double totalTreeBuildTime = 0.0;
    double totalForceTime = 0.0;
    double totalCleanupTime = 0.0;
    particles.reserve(options.particles);

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

        NodePtr* rootPtr = new NodePtr();
        rootPtr->boundsX = centerX;
        rootPtr->boundsY = centerY;
        rootPtr->halfSize = maxHalfSize;

        for (std::size_t i = 0; i < particles.size(); ++i) {
            insertParticlePtr(rootPtr, static_cast<int>(i), particles);
        }
        // if (frame == 0) {
        //     //Particle array size:
        //     size_t particlesMem = particles.capacity() * sizeof(Particle);
        //     // Maximum reserved tree-arena size:
        //     int nodeCount = countNodesPtr(rootPtr);
        //     size_t treeMem = nodeCount * sizeof(NodePtr);

        //     std::cout << std::fixed << std::setprecision(6);
        //     double totalAppMemMB = static_cast<double>(particlesMem + treeMem) / (1024.0 * 1024.0);
        //     std::cout << "Algorithm memory usage: " << totalAppMemMB << " MB\n";
        //     std::cout << "Created " << nodeCount << " tree nodes.\n";
        //     std::cout << "Size of Particle: " << sizeof(Particle) << " bytes\n";
        //     std::cout << "Size of NodePtr (V2): " << sizeof(NodePtr) << " bytes\n";
        // }

        computeMassDistributionPtr(rootPtr, particles);
        const double treeTime = timer.stopTime();
        if (frame >= options.warmupFrames) totalTreeBuildTime += treeTime;

        timer.start();
        for (std::size_t i = 0; i < particles.size(); ++i)
        {
            calculateForcesPtr(static_cast<int>(i), rootPtr, particles);
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

        timer.start();
        deleteTreePtr(rootPtr);
        const double cleanupTime = timer.stopTime();
        if (frame >= options.warmupFrames) totalCleanupTime += cleanupTime;
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
    std::cout << "Cleanup time: " << (totalCleanupTime / options.frames) << " ms / frame\n";
    std::cout << "Total measured time: " << (totalTreeBuildTime + totalForceTime + totalCleanupTime) << " ms\n";
    // std::ifstream outFile("reference_2000k.txt");
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
