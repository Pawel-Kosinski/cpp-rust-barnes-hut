#!/usr/bin/env python3
"""Collect reproducibility metadata without requiring a Git working tree."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def command_version(command: list[str]) -> str:
    executable = shutil.which(command[0])
    if executable is None:
        return "not available"
    try:
        result = subprocess.run(
            [executable, *command[1:]], check=False, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError) as error:
        return f"unavailable: {error}"
    output = result.stdout.strip() or result.stderr.strip()
    return output.splitlines()[0] if output else f"exit code {result.returncode}"


def cpu_model() -> str:
    if sys.platform.startswith("win"):
        try:
            import winreg

            key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
        except OSError:
            pass
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith(("model name", "hardware")):
                return line.split(":", 1)[-1].strip()
    return platform.processor() or "not available"


def physical_core_count() -> int | None:
    if sys.platform.startswith("win"):
        match = re.search(r"(\d+)-Core", cpu_model(), flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        physical_cores: set[tuple[str, str]] = set()
        physical_id = "0"
        core_id = ""
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines() + [""]:
            if line.startswith("physical id"):
                physical_id = line.split(":", 1)[-1].strip()
            elif line.startswith("core id"):
                core_id = line.split(":", 1)[-1].strip()
            elif not line and core_id:
                physical_cores.add((physical_id, core_id))
                core_id = ""
        if physical_cores:
            return len(physical_cores)
    return None


def physical_memory_bytes() -> int | None:
    if sys.platform.startswith("win"):
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.total_physical)
    try:
        return int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))
    except (AttributeError, OSError, ValueError):
        return None


def input_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compile_commands(build_dir: Path) -> list[str]:
    path = build_dir / "compile_commands.json"
    if not path.exists():
        return []
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    commands = {str(entry.get("command") or " ".join(entry.get("arguments", []))) for entry in entries}
    return sorted(command for command in commands if command)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--particles", required=True, type=int)
    parser.add_argument("--frames", required=True, type=int)
    parser.add_argument("--warmup-frames", required=True, type=int)
    parser.add_argument("--repeats", required=True, type=int)
    parser.add_argument("--theta", required=True, type=float)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--requested-threads", required=True, type=int)
    parser.add_argument("--effective-parallel-threads", required=True, type=int)
    parser.add_argument("--languages", required=True)
    parser.add_argument("--variants", required=True)
    parser.add_argument("--build-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    metadata = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source": {"version": arguments.version, "commit": arguments.commit},
        "system": {
            "os": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "cpu_model": cpu_model(),
            "physical_cores": physical_core_count(),
            "logical_cores": os.cpu_count(),
            "physical_memory_bytes": physical_memory_bytes(),
        },
        "toolchain": {
            "cxx": command_version([os.environ.get("CXX", "c++"), "--version"]),
            "cmake": command_version(["cmake", "--version"]),
            "rustc": command_version(["rustc", "--version"]),
            "cargo": command_version(["cargo", "--version"]),
            "python": platform.python_version(),
            "cmake_build_type": "Release",
            "cargo_profile": "release with lto=true and codegen-units=1",
            "cxxflags_environment": os.environ.get("CXXFLAGS", ""),
            "compile_commands": compile_commands(arguments.build_dir),
        },
        "input": {
            "path": str(arguments.input),
            "sha256": input_sha256(arguments.input),
            "particles": arguments.particles,
            "seed": arguments.seed,
        },
        "protocol": {
            "measured_frames": arguments.frames,
            "warmup_frames": arguments.warmup_frames,
            "independent_process_repeats": arguments.repeats,
            "theta": arguments.theta,
            "requested_threads": arguments.requested_threads,
            "effective_parallel_threads": arguments.effective_parallel_threads,
            "languages": arguments.languages.split(","),
            "variants": arguments.variants.split(","),
            "timing_clock": "steady/monotonic wall clock",
        },
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
