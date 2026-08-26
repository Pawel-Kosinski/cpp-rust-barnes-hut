#pragma once

#include <cstddef>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

struct BenchmarkOptions {
    std::string input = "start.txt";
    std::string dumpForces;
    std::size_t particles = 0;
    int frames = 10;
    int warmupFrames = 0;
    float theta = 0.3f;
    int threads = 0;

    int totalFrames() const {
        return warmupFrames + frames;
    }
};

inline void printBenchmarkUsage(const char* program) {
    std::cout << "Usage: " << program
              << " [--input FILE] [--particles N] [--frames N] [--warmup-frames N]"
              << " [--theta VALUE] [--threads N] [--dump-forces FILE]\n";
}

inline bool parseBenchmarkOptions(int argc, char** argv, BenchmarkOptions& options) {
    for (int i = 1; i < argc; ++i) {
        const std::string argument = argv[i];
        if (argument == "--help") {
            printBenchmarkUsage(argv[0]);
            return false;
        }
        if (i + 1 >= argc) {
            std::cerr << "Missing value for " << argument << "\n";
            return false;
        }

        const std::string value = argv[++i];
        try {
            if (argument == "--input") {
                options.input = value;
            } else if (argument == "--dump-forces") {
                options.dumpForces = value;
            } else if (argument == "--particles") {
                options.particles = static_cast<std::size_t>(std::stoull(value));
            } else if (argument == "--frames") {
                options.frames = std::stoi(value);
            } else if (argument == "--warmup-frames") {
                options.warmupFrames = std::stoi(value);
            } else if (argument == "--theta") {
                options.theta = std::stof(value);
            } else if (argument == "--threads") {
                options.threads = std::stoi(value);
            } else {
                std::cerr << "Unknown option: " << argument << "\n";
                return false;
            }
        } catch (const std::exception&) {
            std::cerr << "Invalid value for " << argument << ": " << value << "\n";
            return false;
        }
    }

    if (options.frames <= 0 || options.warmupFrames < 0 || options.theta <= 0.0f || options.threads < 0) {
        std::cerr << "frames and theta must be positive; warm-up frames and threads cannot be negative.\n";
        return false;
    }
    return true;
}

template <typename ParticleRange>
bool writeForces(const std::string& path, const ParticleRange& particles) {
    if (path.empty()) return true;

    std::ofstream output(path);
    if (!output) {
        std::cerr << "Could not write force snapshot: " << path << "\n";
        return false;
    }

    output << "index,acc_x,acc_y\n" << std::setprecision(9);
    std::size_t index = 0;
    for (const auto& particle : particles) {
        output << index++ << ',' << particle.accX << ',' << particle.accY << '\n';
    }
    return true;
}

inline bool validateParticleCount(const BenchmarkOptions& options, std::size_t loaded) {
    if (loaded == 0) {
        std::cerr << "Input contains no particles.\n";
        return false;
    }
    if (options.particles != 0 && options.particles != loaded) {
        std::cerr << "Input contains " << loaded << " particles but --particles requested "
                  << options.particles << ".\n";
        return false;
    }
    return true;
}
