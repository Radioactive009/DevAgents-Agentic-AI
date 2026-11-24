"""
Evaluation and Benchmarking Module for DevAgents-AGI.

Provides:
- Model pricing catalog and token cost computation (pricing.py)
- Performance, token, cost, and latency evaluation suite (cost_benchmark.py)
"""

from src.evaluation.pricing import (
    ModelPricing,
    calculate_token_cost,
    get_model_pricing,
    get_supported_models,
    normalize_model_name,
)
from src.evaluation.cost_benchmark import (
    BenchmarkRun,
    BenchmarkReport,
    calculate_percentile,
    export_to_csv,
    export_to_json,
    run_cost_benchmark,
)

__all__ = [
    "ModelPricing",
    "calculate_token_cost",
    "get_model_pricing",
    "get_supported_models",
    "normalize_model_name",
    "BenchmarkRun",
    "BenchmarkReport",
    "calculate_percentile",
    "export_to_csv",
    "export_to_json",
    "run_cost_benchmark",
]
