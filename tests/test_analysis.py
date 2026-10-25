from app.services.analysis import benchmark_cipher, estimate_energy, run_avalanche_analysis


def test_analysis_result_shape():
    result = run_avalanche_analysis(0xBEEF, 6, samples=16)
    assert 0 <= result["average_percent"] <= 100
    assert result["observations"] == 16 * 8
    assert len(result["heatmap"]) == 8
    assert all(len(row) == 8 for row in result["heatmap"])


def test_benchmark_and_energy_are_positive():
    benchmark = benchmark_cipher(0xBEEF, 4, iterations=1000)
    assert benchmark["average_us"] > 0
    energy = estimate_energy(benchmark["average_us"])
    assert energy["estimated_energy_uj"] > 0

