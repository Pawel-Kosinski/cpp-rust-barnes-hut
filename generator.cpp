#include <iostream>
#include <fstream>
#include <cstdlib>

constexpr int NUM_PARTICLES = 10000;

int main()
{
    srand(42); // Zamrożone ziarno losowości
    std::ofstream outFile("start_10k.txt");
    
    if (!outFile)
    {
        std::cerr << "Blad: Nie mozna utworzyc pliku start_10k.txt!\n";
        return 1;
    }

    for (int i = 0; i < NUM_PARTICLES; ++i)
    {
        float velocityX = (static_cast<float>(rand()) / RAND_MAX * 50.0f) - 25.0f;
        float velocityY = (static_cast<float>(rand()) / RAND_MAX * 50.0f) - 25.0f;
        float mass = static_cast<float>(rand()) / RAND_MAX * 10.0f;
        float posX = static_cast<float>(rand()) / RAND_MAX * 100.0f;
        float posY = static_cast<float>(rand()) / RAND_MAX * 100.0f;

        // Zapis: X Y Vx Vy Masa
        outFile << posX << " " << posY << " " << velocityX << " " << velocityY << " " << mass << "\n";
    }

    outFile.close();
    std::cout << "Pangeneza! Zapisano " << NUM_PARTICLES << " czastek do start_10k.txt\n";
    return 0;
}