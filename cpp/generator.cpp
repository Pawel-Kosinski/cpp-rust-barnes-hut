#include <iostream>
#include <fstream>
#include <cstdlib>
#include <cmath>

constexpr int NUM_PARTICLES = 10000;
constexpr float G = 1.0f;
constexpr float PI = 3.14159265359f;

int main()
{
    srand(42); // Zamrożone ziarno
    std::ofstream outFile("start_10k.txt");

    if (!outFile) {
        std::cerr << "Blad zapisu pliku!\n";
        return 1;
    }

    // Parametry galaktyki
    float centerX = 500.0f;
    float centerY = 500.0f;
    float centerMass = 100000.0f;
    float galaxyRadius = 400.0f;

    outFile << centerX << " " << centerY << " 0.0 0.0 " << centerMass << "\n";

    
    for (int i = 1; i < NUM_PARTICLES; ++i)
    {
        float r = std::sqrt(static_cast<float>(rand()) / RAND_MAX) * galaxyRadius + 5.0f; 
        float theta = static_cast<float>(rand()) / RAND_MAX * 2.0f * PI;

        float posX = centerX + r * std::cos(theta);
        float posY = centerY + r * std::sin(theta);

        float v = std::sqrt(G * centerMass / r);


        float perturbation = (static_cast<float>(rand()) / RAND_MAX * 0.4f) + 0.8f; 
        v *= perturbation;

        float velocityX = -v * std::sin(theta);
        float velocityY =  v * std::cos(theta);

        float mass = (static_cast<float>(rand()) / RAND_MAX * 5.0f) + 1.0f;

        outFile << posX << " " << posY << " " << velocityX << " " << velocityY << " " << mass << "\n";
    }

    outFile.close();
    std::cout << "Pangeneza udana! Wygenerowano model galaktyki dyskowej.\n";
    return 0;
}