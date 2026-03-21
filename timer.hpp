#include <chrono>
#include <string>

struct Timer
{
    std::chrono::time_point<std::chrono::high_resolution_clock> start_time;

    void start() 
    {
        start_time = std::chrono::high_resolution_clock::now();
    }

    float stop() 
    {
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
        return duration.count() / 1000.0f; 
    }
};