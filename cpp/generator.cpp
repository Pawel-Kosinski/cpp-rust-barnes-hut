#include <iostream>
#include <fstream>
#include <cmath>
#include <random>
#include <iomanip>

constexpr int NUM_PARTICLES = 10000000;
constexpr float PI = 3.14159265359f;
constexpr float G = 1.0f; 

int main()
{
    std::mt19937 rng(1337);
    std::uniform_real_distribution<float> dist(0.0f, 1.0f);
    
    std::ofstream outFile("start_10kk.txt");
    if (!outFile) {
        std::cerr << "Error while writing the file!\n";
        return 1;
    }

    float centerX = 500.0f;
    float centerY = 500.0f;
    float a = 100.0f;           
    float maxRadius = 400.0f;   
    float particleMass = 2.0f;  
    
    float totalMass = NUM_PARTICLES * particleMass;

    for (int i = 0; i < NUM_PARTICLES; ++i)
    {
        float r;
        // Correct tail truncation (rejection sampling)
        // Instead of clamping particles to the boundary, sample until accepted.
        do {
            float u = dist(rng);
            // Zabezpieczenie tylko przed u=1.0 (dzielenie przez zero)
            u = std::min(u, 0.999f); 
            r = a * std::sqrt(u / (1.0f - u));
        } while (r > maxRadius);

        float theta = dist(rng) * 2.0f * PI;

        float posX = centerX + r * std::cos(theta);
        float posY = centerY + r * std::sin(theta);

        // Orbital velocity initialization
        // Compute enclosed mass within radius R for the 2D Plummer distribution
        float masEnclosed = totalMass * (r * r) / (r * r + a * a);
        
        // Circular-orbit velocity formula with softened epsilon
        float vCirc = std::sqrt((G * masEnclosed) / (r + 0.1f)); 
        
        // The only perturbation used here breaks perfect symmetry (+/- 15%)
        float perturbation = 0.85f + dist(rng) * 0.30f;
        float v = vCirc * perturbation;

        float velocityX = -v * std::sin(theta);
        float velocityY =  v * std::cos(theta);
        outFile << std::fixed << std::setprecision(6);

        outFile << posX << " " << posY << " " 
                << velocityX << " " << velocityY << " " 
                << particleMass << "\n";
    }

    outFile.close();
    std::cout << "Wygenerowano stabilna gromade Plummera (Poprawiona).\n";
    return 0;
}