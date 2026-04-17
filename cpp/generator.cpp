#include <iostream>
#include <fstream>
#include <cmath>
#include <random>

constexpr int NUM_PARTICLES = 50000;
constexpr float PI = 3.14159265359f;
constexpr float G = 1.0f; // Dodano brakujące G

int main()
{
    std::mt19937 rng(1337);
    std::uniform_real_distribution<float> dist(0.0f, 1.0f);
    
    std::ofstream outFile("start_50k.txt");
    if (!outFile) {
        std::cerr << "Blad zapisu pliku!\n";
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
        // PRAWIDŁOWE ODCIĘCIE OGONÓW (Rejection Sampling)
        // Zamiast lepić cząstki do krawędzi, losujemy do skutku.
        do {
            float u = dist(rng);
            // Zabezpieczenie tylko przed u=1.0 (dzielenie przez zero)
            u = std::min(u, 0.999f); 
            r = a * std::sqrt(u / (1.0f - u));
        } while (r > maxRadius);

        float theta = dist(rng) * 2.0f * PI;

        float posX = centerX + r * std::cos(theta);
        float posY = centerY + r * std::sin(theta);

        // PRAWIDŁOWA FIZYKA ORBITALNA
        // Obliczamy masę zamkniętą wewnątrz promienia R dla 2D Plummera
        float masEnclosed = totalMass * (r * r) / (r * r + a * a);
        
        // Czysty wzór na prędkość na orbicie kołowej (zmiękczony epsilonem)
        float vCirc = std::sqrt((G * masEnclosed) / (r + 0.1f)); 
        
        // JEDYNY dopuszczalny szum to ten łamiący idealną symetrię (tu: +/- 15%)
        float perturbation = 0.85f + dist(rng) * 0.30f;
        float v = vCirc * perturbation;

        float velocityX = -v * std::sin(theta);
        float velocityY =  v * std::cos(theta);

        outFile << posX << " " << posY << " " 
                << velocityX << " " << velocityY << " " 
                << particleMass << "\n";
    }

    outFile.close();
    std::cout << "Wygenerowano stabilna gromade Plummera (Poprawiona).\n";
    return 0;
}