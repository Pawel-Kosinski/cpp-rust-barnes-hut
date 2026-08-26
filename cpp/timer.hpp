#include <chrono>

struct Timer
{
    using Clock = std::chrono::steady_clock;
    std::chrono::time_point<Clock> start_time;

    void start() 
    {
        start_time = Clock::now();
    }

    double stopTime()
    {
        const auto end_time = Clock::now();
        return std::chrono::duration<double, std::milli>(end_time - start_time).count();
    }

};
