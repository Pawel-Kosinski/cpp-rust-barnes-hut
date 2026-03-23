#include <chrono>
#include <string>
#include <intrin.h>

struct Timer
{
    std::chrono::time_point<std::chrono::high_resolution_clock> start_time;
    unsigned long long start_cycles;

    void start() 
    {
        start_time = std::chrono::high_resolution_clock::now();
        start_cycles = __rdtsc();
    }

    float stopTime() 
    {
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
        return duration.count() / 1000.0f; 
    }

    unsigned long long stopCycles()
    {
        unsigned long long end_cycles = __rdtsc();
        return end_cycles - start_cycles;
    }
};