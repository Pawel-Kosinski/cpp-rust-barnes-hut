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
    float centerX = 500.0f; // Środek układu przeniesiony dalej od (0,0)
    float centerY = 500.0f;
    float centerMass = 100000.0f; // Supermasywna Czarna Dziura (SMBH)
    float galaxyRadius = 400.0f;

    // CZĄSTKA 0: CZARNA DZIURA W CENTRUM (X Y Vx Vy Masa)
    // Ma potężną masę i prędkość 0.0, będzie kotwicą całego układu.
    outFile << centerX << " " << centerY << " 0.0 0.0 " << centerMass << "\n";

    // CZĄSTKI 1 - 9999: GWIAZDY NA ORBITACH
    for (int i = 1; i < NUM_PARTICLES; ++i)
    {
        // 1. Losujemy pozycję na dysku (im bliżej centrum, tym gęściej)
        // Pierwiastkowanie zapewnia bardziej realistyczny rozkład gwiazd
        float r = std::sqrt(static_cast<float>(rand()) / RAND_MAX) * galaxyRadius + 5.0f; 
        float theta = static_cast<float>(rand()) / RAND_MAX * 2.0f * PI;

        float posX = centerX + r * std::cos(theta);
        float posY = centerY + r * std::sin(theta);

        // 2. Liczymy wymaganą prędkość do utrzymania orbity kołowej
        float v = std::sqrt(G * centerMass / r);

        // 3. Dodajemy zjawisko "dyspersji prędkości" (szum orbity 0.8 do 1.2)
        // Dzięki temu nie tworzymy sztywnej płyty, lecz płynny gaz/gwiazdy.
        float perturbation = (static_cast<float>(rand()) / RAND_MAX * 0.4f) + 0.8f; 
        v *= perturbation;

        // 4. Ustawiamy wektor prędkości prostopadle do promienia (ruch obrotowy przeciwny do wskazówek zegara)
        float velocityX = -v * std::sin(theta);
        float velocityY =  v * std::cos(theta);

        // 5. Losujemy masę gwiazdy (od 1.0 do 6.0)
        float mass = (static_cast<float>(rand()) / RAND_MAX * 5.0f) + 1.0f;

        // Zapisujemy w naszym ustalonym formacie
        outFile << posX << " " << posY << " " << velocityX << " " << velocityY << " " << mass << "\n";
    }

    outFile.close();
    std::cout << "Pangeneza udana! Wygenerowano model galaktyki dyskowej.\n";
    return 0;
}