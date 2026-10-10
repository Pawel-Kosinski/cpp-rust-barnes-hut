#pragma once

#include <algorithm>
#include <cstddef>
#include <cmath>
#include <limits>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

struct BenchmarkOptions {
    std::string input = "start.txt";
    std::string dumpForces;
    std::string dumpState;
    std::string diagnostics;
    std::string memoryReport;
    std::size_t diagnosticStride = 1;
    std::size_t forceSamples = 0;
    float timeStep = 0.016f;
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
              << " [--theta VALUE] [--threads N] [--dump-forces FILE] [--force-samples N]"
              << " [--dt VALUE] [--diagnostics FILE] [--diagnostic-stride N]"
              << " [--dump-state FILE] [--memory-report FILE]\n";
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
            } else if (argument == "--dump-state") {
                options.dumpState = value;
            } else if (argument == "--diagnostics") {
                options.diagnostics = value;
            } else if (argument == "--memory-report") {
                options.memoryReport = value;
            } else if (argument == "--dt") {
                options.timeStep = std::stof(value);
            } else if (argument == "--diagnostic-stride" || argument == "--force-samples") {
                if (value.empty() || value.front() == '-') throw std::invalid_argument("negative count");
                const auto count = static_cast<std::size_t>(std::stoull(value));
                if (argument == "--diagnostic-stride") options.diagnosticStride = count;
                else options.forceSamples = count;
            } else if (argument == "--particles") {
                if (value.empty() || value.front() == '-') throw std::invalid_argument("negative count");
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

    if (options.frames <= 0 || options.warmupFrames < 0 || !std::isfinite(options.theta)
        || options.theta <= 0.0f || options.threads < 0 || !std::isfinite(options.timeStep)
        || options.timeStep <= 0.0f || options.diagnosticStride == 0
        || options.warmupFrames > std::numeric_limits<int>::max() - options.frames) {
        std::cerr << "Invalid frame count, theta, timestep, stride, or thread count.\n";
        return false;
    }
    return true;
}

template <typename ParticleRange>
bool writeForces(const std::string& path, const ParticleRange& particles, std::size_t samples = 0) {
    if (path.empty()) return true;

    std::ofstream output(path);
    if (!output) {
        std::cerr << "Could not write force snapshot: " << path << "\n";
        return false;
    }

    output << "index,acc_x,acc_y\n" << std::setprecision(9);
    const std::size_t count = samples == 0 ? particles.size() : std::min(samples, particles.size());
    for (std::size_t k = 0; k < count; ++k) {
        const std::size_t index = count <= 1 ? 0 : k * (particles.size() - 1) / (count - 1);
        const auto& particle = particles[index];
        output << index << ',' << particle.accX << ',' << particle.accY << '\n';
    }
    output.flush();
    return static_cast<bool>(output);
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
