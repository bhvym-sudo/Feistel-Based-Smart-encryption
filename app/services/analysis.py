"""Repeatable cryptographic experiments used by the API and dashboard."""

from __future__ import annotations

import random
import statistics
import time

from app.core.cipher import FeistelCipher, hamming_distance


def run_avalanche_analysis(key: int, rounds: int, samples: int = 128, seed: int = 7) -> dict[str, object]:
    samples = max(16, min(samples, 512))
    rng = random.Random(seed)
    cipher = FeistelCipher(key, rounds)
    distances: list[int] = []
    matrix = [[0.0 for _ in range(8)] for _ in range(8)]
    per_input_counts = [0 for _ in range(8)]

    for _ in range(samples):
        plaintext = rng.randrange(256)
        baseline = cipher.encrypt(plaintext)
        for input_bit in range(8):
            modified = cipher.encrypt(plaintext ^ (1 << input_bit))
            delta = baseline ^ modified
            distance = hamming_distance(baseline, modified)
            distances.append(distance)
            per_input_counts[input_bit] += 1
            for output_bit in range(8):
                matrix[input_bit][output_bit] += (delta >> output_bit) & 1

    for input_bit in range(8):
        count = per_input_counts[input_bit]
        matrix[input_bit] = [round(value / count * 100, 1) for value in matrix[input_bit]]

    distribution = {str(changes): distances.count(changes) for changes in range(9)}
    average_bits = statistics.mean(distances)
    return {
        "average_changed_bits": round(average_bits, 3),
        "average_percent": round(average_bits / 8 * 100, 2),
        "standard_deviation": round(statistics.pstdev(distances), 3),
        "observations": len(distances),
        "distribution": distribution,
        "heatmap": matrix,
    }


def run_key_sensitivity(key: int, rounds: int, samples: int = 128, seed: int = 13) -> dict[str, float | int]:
    rng = random.Random(seed)
    distances: list[int] = []
    base = FeistelCipher(key, rounds)
    for _ in range(samples):
        plaintext = rng.randrange(256)
        key_bit = rng.randrange(16)
        changed = FeistelCipher(key ^ (1 << key_bit), rounds)
        distances.append(hamming_distance(base.encrypt(plaintext), changed.encrypt(plaintext)))
    average = statistics.mean(distances)
    return {
        "average_changed_bits": round(average, 3),
        "average_percent": round(average / 8 * 100, 2),
        "observations": len(distances),
    }


def benchmark_cipher(key: int, rounds: int, iterations: int = 20_000) -> dict[str, float | int]:
    iterations = max(1_000, min(iterations, 200_000))
    cipher = FeistelCipher(key, rounds)
    batch_count = min(20, max(5, iterations // 1_000))
    batch_size, remainder = divmod(iterations, batch_count)
    batch_averages_ns: list[float] = []
    checksum = 0

    # Warm up the interpreter before collecting the timed batches.
    for plaintext in range(256):
        checksum ^= cipher.encrypt(plaintext)

    completed = 0
    total_ns = 0
    for batch_index in range(batch_count):
        current_size = batch_size + (1 if batch_index < remainder else 0)
        started = time.perf_counter_ns()
        for offset in range(current_size):
            checksum ^= cipher.encrypt((completed + offset) & 0xFF)
        elapsed_ns = time.perf_counter_ns() - started
        total_ns += elapsed_ns
        completed += current_size
        batch_averages_ns.append(elapsed_ns / current_size)

    average_ns = total_ns / iterations
    batch_std_ns = statistics.pstdev(batch_averages_ns)
    return {
        "iterations": iterations,
        "batches": batch_count,
        "total_ms": round(total_ns / 1_000_000, 3),
        "average_us": round(average_ns / 1_000, 4),
        "minimum_us": round(min(batch_averages_ns) / 1_000, 4),
        "maximum_us": round(max(batch_averages_ns) / 1_000, 4),
        "standard_deviation_us": round(batch_std_ns / 1_000, 4),
        "throughput_blocks_per_second": round(1_000_000_000 / average_ns, 1),
        "checksum": checksum,
    }


def estimate_energy(average_us: float, voltage: float = 3.3, active_current_ma: float = 8.0) -> dict[str, float]:
    estimated_power_mw = voltage * active_current_ma
    energy_microjoules = estimated_power_mw * average_us / 1_000
    return {
        "voltage_v": voltage,
        "active_current_ma": active_current_ma,
        "estimated_power_mw": round(estimated_power_mw, 4),
        "estimated_energy_uj": round(energy_microjoules, 6),
    }

