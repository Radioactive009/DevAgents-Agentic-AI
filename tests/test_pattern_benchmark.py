"""
Unit and Integration Tests for Agentic Design Patterns Formal Comparative Evaluation (Requirement 4).

Validates:
1. evaluate_agentic_patterns execution across diverse run counts and seed reproducibility.
2. Metrics calculation accuracy (latency percentiles, tokens, dollar costs, MTTR, success rate, bloat factor).
3. State safety and concurrency race resistance (Blackboard RLock vs uncoordinated memory).
4. Context token bloat factor quantification (O(N) ReAct growth vs O(1) Blackboard isolation).
5. PatternTradeoffReport generation, recommendations, and multi-dimensional trade-off matrix.
6. Pydantic schema validation, property accessors, and dictionary-style access ergonomics.
7. CSV and JSON export formatting, exact schema validation, and round-trip deserialization.
8. Standalone CLI runner argument parsing, ASCII table formatting, and exit codes.
"""

from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from pathlib import Path
import pytest
import sys

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from src.evaluation.pattern_benchmark import (
    DEFAULT_BENCHMARK_MODEL,
    PatternBenchmarkMetrics,
    PatternComparisonResult,
    PatternRunDetail,
    PatternTradeoffReport,
    PatternType,
    evaluate_agentic_patterns,
    export_pattern_benchmark_to_csv,
    export_pattern_benchmark_to_json,
    generate_pattern_tradeoff_report,
    test_blackboard_concurrency_safety as verify_blackboard_concurrency_safety,
    test_uncoordinated_concurrency_safety as verify_uncoordinated_concurrency_safety,
)
from src.evaluation.pricing import calculate_token_cost, normalize_model_name
import compare_agentic_patterns


# ==============================================================================
# 1. CORE EVALUATION EXECUTION TESTS
# ==============================================================================

class TestEvaluateAgenticPatternsExecution:
    """Tests for evaluate_agentic_patterns function with varying run parameters."""

    def test_evaluate_patterns_default_parameters(self):
        """Verifies evaluation with default parameters (runs=5, mock=True)."""
        result = evaluate_agentic_patterns(runs=5, mock=True, seed=123)
        assert isinstance(result, PatternComparisonResult)
        assert result.runs_per_pattern == 5
        assert result.model == DEFAULT_BENCHMARK_MODEL
        assert len(result.patterns) == 3

        expected_patterns = {
            PatternType.BLACKBOARD_EVALUATOR_OPTIMIZER.value,
            PatternType.REACT.value,
            PatternType.HIERARCHICAL.value,
        }
        assert set(result.patterns.keys()) == expected_patterns

    @pytest.mark.parametrize("runs_count", [1, 2, 4])
    def test_evaluate_patterns_varying_run_counts(self, runs_count: int):
        """Verifies evaluation succeeds with different run counts."""
        result = evaluate_agentic_patterns(runs=runs_count, mock=True, seed=42)
        assert result.runs_per_pattern == runs_count
        for name, metrics in result.patterns.items():
            assert metrics.total_runs == runs_count
            assert len(metrics.runs) == runs_count

    def test_evaluate_patterns_invalid_runs_raises_error(self):
        """Verifies that runs < 1 raises ValueError."""
        with pytest.raises(ValueError, match="runs must be >= 1"):
            evaluate_agentic_patterns(runs=0, mock=True)

        with pytest.raises(ValueError, match="runs must be >= 1"):
            evaluate_agentic_patterns(runs=-5, mock=True)

    def test_evaluate_patterns_seed_reproducibility(self):
        """Verifies that providing identical seeds yields deterministic metrics."""
        res1 = evaluate_agentic_patterns(runs=3, mock=True, seed=999)
        res2 = evaluate_agentic_patterns(runs=3, mock=True, seed=999)

        for pat in res1.patterns:
            m1 = res1.patterns[pat]
            m2 = res2.patterns[pat]
            assert m1.total_prompt_tokens == m2.total_prompt_tokens
            assert m1.total_completion_tokens == m2.total_completion_tokens
            assert m1.total_cost_usd == m2.total_cost_usd
            assert m1.mean_recovery_attempts == m2.mean_recovery_attempts

    def test_evaluate_patterns_with_different_pricing_models(self):
        """Verifies evaluation operates across different pricing catalog models."""
        # LLaMA 3.1 8B instant (lower cost model)
        res_llama = evaluate_agentic_patterns(
            runs=2, mock=True, model="groq/llama-3.1-8b-instant", seed=10
        )
        assert res_llama.model == "groq/llama-3.1-8b-instant"

        # Gemini 1.5 Flash
        res_gemini = evaluate_agentic_patterns(
            runs=2, mock=True, model="gemini-1.5-flash", seed=10
        )
        assert res_gemini.model == "gemini/gemini-1.5-flash"

        # LLaMA 8B has different cost than Gemini 1.5 Flash
        bb_llama = res_llama.patterns[PatternType.BLACKBOARD_EVALUATOR_OPTIMIZER.value]
        bb_gemini = res_gemini.patterns[PatternType.BLACKBOARD_EVALUATOR_OPTIMIZER.value]
        assert bb_llama.total_cost_usd > 0.0
        assert bb_gemini.total_cost_usd > 0.0

    def test_evaluate_patterns_invalid_model_raises_error(self):
        """Verifies that unsupported model names raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported model"):
            evaluate_agentic_patterns(runs=2, mock=True, model="invalid-ai-model-xyz")


# ==============================================================================
# 2. METRICS CALCULATION ACCURACY TESTS
# ==============================================================================

class TestMetricsCalculationAccuracy:
    """Tests accuracy of statistical metrics, percentiles, token accounting, and MTTR."""

    def test_latency_statistics_and_percentiles(self):
        """Validates that P50, P90, P95, min, max, and mean latencies satisfy mathematical invariants."""
        result = evaluate_agentic_patterns(runs=5, mock=True, seed=77)
        for name, m in result.patterns.items():
            assert m.min_latency_s <= m.mean_latency_s <= m.max_latency_s
            assert m.min_latency_s <= m.p50_latency_s <= m.max_latency_s
            assert m.p50_latency_s <= m.p90_latency_s <= m.p95_latency_s
            assert m.mean_latency_s > 0.0

    def test_token_accounting_and_cost_consistency(self):
        """Validates token sums and pricing calculation alignment with calculate_token_cost."""
        model = "groq/qwen/qwen3.8-27b"
        result = evaluate_agentic_patterns(runs=3, mock=True, seed=88, model=model)

        for name, m in result.patterns.items():
            # Prompt + completion == total tokens
            assert m.total_prompt_tokens + m.total_completion_tokens == m.total_tokens
            assert math.isclose(m.avg_tokens, m.total_tokens / m.total_runs, rel_tol=1e-3)

            # Recomputed cost matches total_cost_usd
            expected_cost = calculate_token_cost(model, m.total_prompt_tokens, m.total_completion_tokens)
            assert math.isclose(m.total_cost_usd, expected_cost, rel_tol=1e-6)

            # Cost per 1k requests matches avg_cost * 1000
            assert math.isclose(m.cost_per_1k_requests, m.avg_cost_usd * 1000.0, rel_tol=1e-3)

    def test_error_recovery_and_mttr_calculation(self):
        """Validates recovery rate percentage and MTTR (mean attempts to recover)."""
        result = evaluate_agentic_patterns(runs=5, mock=True, seed=99)
        bb = result.patterns[PatternType.BLACKBOARD_EVALUATOR_OPTIMIZER.value]
        react = result.patterns[PatternType.REACT.value]

        # Recovery rate is between 0% and 100%
        assert 0.0 <= bb.recovery_rate_pct <= 100.0
        assert 0.0 <= react.recovery_rate_pct <= 100.0

        # Mean recovery attempts is positive
        assert bb.mean_recovery_attempts >= 1.0
        assert react.mean_recovery_attempts >= 1.0

        # Mean recovery duration is positive
        assert bb.mttr_seconds > 0.0
        assert react.mttr_seconds > 0.0

    def test_context_token_bloat_factor_quantification(self):
        """
        Validates context token bloat factor:
        - Blackboard + Evaluator-Optimizer achieves O(1) isolated context (bloat factor == 1.0).
        - ReAct exhibits cumulative O(N) conversational growth (bloat factor >= 1.7x).
        - Hierarchical exhibits scoped bounded context (bloat factor ~1.25x - 1.35x).
        """
        result = evaluate_agentic_patterns(runs=3, mock=True, seed=1234)
        bb = result.patterns[PatternType.BLACKBOARD_EVALUATOR_OPTIMIZER.value]
        react = result.patterns[PatternType.REACT.value]
        hier = result.patterns[PatternType.HIERARCHICAL.value]

        # Blackboard context is strictly isolated per attempt
        assert bb.context_token_bloat_factor == 1.0

        # ReAct cumulative context causes significant bloat
        assert react.context_token_bloat_factor >= 1.7
        assert react.context_token_bloat_factor > hier.context_token_bloat_factor
        assert hier.context_token_bloat_factor > bb.context_token_bloat_factor


# ==============================================================================
# 3. STATE SAFETY & CONCURRENCY RACE RESISTANCE TESTS
# ==============================================================================

class TestStateSafetyAndConcurrency:
    """Tests thread-safety and race resistance under concurrent state access."""

    def test_blackboard_concurrency_safety_verifies_rlock_protection(self):
        """Validates that Blackboard with RLock achieves 100% race-free mutation execution."""
        concurrency_report = verify_blackboard_concurrency_safety(
            num_threads=8, operations_per_thread=10
        )
        assert concurrency_report["concurrency_safe"] is True
        assert concurrency_report["race_detected"] is False
        assert concurrency_report["actual_mutations"] == concurrency_report["expected_mutations"]
        assert concurrency_report["race_resistance_rate"] == 100.0

    def test_uncoordinated_concurrency_safety_detects_race_conditions(self):
        """Validates that uncoordinated memory without synchronization suffers race conditions."""
        uncoordinated_report = verify_uncoordinated_concurrency_safety(
            num_threads=8, operations_per_thread=20
        )
        # Under uncoordinated access with yielding, race condition should occur
        concurrency_report_detected = (
            uncoordinated_report["race_detected"] or uncoordinated_report["race_resistance_rate"] < 100.0
        )
        assert concurrency_report_detected is True

    def test_pattern_metrics_concurrency_safety_flags(self):
        """Validates concurrency_safe boolean and state_safety_score per pattern."""
        result = evaluate_agentic_patterns(runs=2, mock=True, seed=55)
        bb = result.patterns[PatternType.BLACKBOARD_EVALUATOR_OPTIMIZER.value]
        react = result.patterns[PatternType.REACT.value]
        hier = result.patterns[PatternType.HIERARCHICAL.value]

        # Blackboard is 100% thread-safe
        assert bb.concurrency_safe is True
        assert bb.state_safety_score == 10.0
        assert bb.race_resistance_rate == 100.0

        # ReAct is uncoordinated and race-prone
        assert react.concurrency_safe is False
        assert react.state_safety_score < 7.0

        # Hierarchical has good scoped worker isolation
        assert hier.concurrency_safe is True
        assert hier.state_safety_score >= 7.5


# ==============================================================================
# 4. TRADE-OFF MATRIX & REPORT GENERATION TESTS
# ==============================================================================

class TestTradeoffReportGeneration:
    """Tests for generate_pattern_tradeoff_report and architectural recommendations."""

    def test_generate_report_from_existing_result(self):
        """Verifies report generation when given pre-computed PatternComparisonResult."""
        result = evaluate_agentic_patterns(runs=3, mock=True, seed=333)
        report = generate_pattern_tradeoff_report(result=result)

        assert isinstance(report, PatternTradeoffReport)
        assert report.model == result.model
        assert len(report.tradeoff_matrix) == 3
        assert len(report.recommendations) >= 3
        assert "best_overall_pattern" in report.comparison_summary

    def test_generate_report_without_existing_result(self):
        """Verifies report generation executes fresh benchmark when result is None."""
        report = generate_pattern_tradeoff_report(result=None, runs=2)
        assert isinstance(report, PatternTradeoffReport)
        assert report.model == DEFAULT_BENCHMARK_MODEL
        assert len(report.detailed_metrics) == 3

    def test_tradeoff_matrix_dimensions_and_fields(self):
        """Validates that all required architectural trade-off dimensions exist for each pattern."""
        report = generate_pattern_tradeoff_report(runs=2)
        required_keys = [
            "architecture_complexity",
            "context_token_scaling",
            "fault_tolerance",
            "concurrency_safety",
            "error_recovery_rate_pct",
            "mean_recovery_attempts",
            "context_bloat_factor",
            "state_safety_score",
            "best_fit_use_cases",
        ]

        for pat_name, matrix in report.tradeoff_matrix.items():
            for key in required_keys:
                assert key in matrix, f"Key '{key}' missing in trade-off matrix for {pat_name}"

    def test_rankings_structure_and_categories(self):
        """Validates that comparative rankings cover all primary optimization criteria."""
        result = evaluate_agentic_patterns(runs=3, mock=True, seed=12)
        assert "fastest_latency" in result.rankings
        assert "lowest_cost" in result.rankings
        assert "highest_error_recovery" in result.rankings
        assert "highest_concurrency_safety" in result.rankings
        assert "lowest_context_bloat" in result.rankings
        assert "overall_composite" in result.rankings

        # Blackboard is top-ranked for lowest bloat and highest safety
        assert result.rankings["lowest_context_bloat"][0] == PatternType.BLACKBOARD_EVALUATOR_OPTIMIZER.value
        assert result.rankings["highest_concurrency_safety"][0] == PatternType.BLACKBOARD_EVALUATOR_OPTIMIZER.value


# ==============================================================================
# 5. SCHEMA ERGONOMICS & DICTIONARY ACCESS TESTS
# ==============================================================================

class TestSchemaErgonomics:
    """Tests dictionary-style access and accessor methods on Pydantic models."""

    def test_pattern_metrics_dictionary_style_access(self):
        """Verifies PatternBenchmarkMetrics supports [] operator and .get()."""
        result = evaluate_agentic_patterns(runs=1, mock=True, seed=1)
        bb = result.patterns[PatternType.BLACKBOARD_EVALUATOR_OPTIMIZER.value]

        assert bb["pattern_name"] == PatternType.BLACKBOARD_EVALUATOR_OPTIMIZER.value
        assert bb["total_runs"] == 1
        assert bb.get("mean_latency_s") > 0.0
        assert bb.get("non_existent_key", "default_val") == "default_val"

    def test_pattern_comparison_result_methods(self):
        """Verifies PatternComparisonResult.get_pattern() and dictionary access."""
        result = evaluate_agentic_patterns(runs=1, mock=True, seed=1)

        # Exact match
        bb = result.get_pattern("Blackboard + Evaluator-Optimizer")
        assert bb is not None
        assert bb.pattern_name == "Blackboard + Evaluator-Optimizer"

        # Case-insensitive substring match
        react = result.get_pattern("react")
        assert react is not None
        assert react.pattern_name == "ReAct"

        # Unknown pattern
        unknown = result.get_pattern("NonExistentPattern")
        assert unknown is None

        # Dict access on result
        assert result["model"] == DEFAULT_BENCHMARK_MODEL
        assert result.get("runs_per_pattern") == 1

    def test_pattern_tradeoff_report_dictionary_and_iteration_protocols(self):
        """Verifies PatternTradeoffReport implements dict-like iteration (keys, values, items, in)."""
        report = generate_pattern_tradeoff_report(runs=1)
        assert "model" in report
        assert "tradeoff_matrix" in report
        assert report["model"] == DEFAULT_BENCHMARK_MODEL
        assert len(list(report.keys())) > 0
        assert len(list(report.values())) > 0
        assert len(list(report.items())) > 0


# ==============================================================================
# 6. JSON & CSV EXPORT TESTS
# ==============================================================================

class TestBenchmarkExports:
    """Tests file export formatting, schema conformance, and round-trip deserialization."""

    def test_export_to_json_and_roundtrip_deserialization(self, tmp_path: Path):
        """Verifies JSON export and deserialization back into PatternComparisonResult."""
        json_file = tmp_path / "exports" / "benchmark_test.json"
        result = evaluate_agentic_patterns(runs=2, mock=True, seed=44)

        export_pattern_benchmark_to_json(result, str(json_file))
        assert json_file.exists()

        with open(json_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        assert "model" in raw_data
        assert "runs_per_pattern" in raw_data
        assert "patterns" in raw_data
        assert "rankings" in raw_data
        assert "tradeoff_matrix" in raw_data

        # Round-trip Pydantic validation
        deserialized = PatternComparisonResult.model_validate(raw_data)
        assert deserialized.runs_per_pattern == 2
        assert len(deserialized.patterns) == 3

    def test_export_tradeoff_report_to_json(self, tmp_path: Path):
        """Verifies exporting PatternTradeoffReport directly to JSON."""
        json_file = tmp_path / "tradeoff_report.json"
        report = generate_pattern_tradeoff_report(runs=2)
        export_pattern_benchmark_to_json(report, str(json_file))

        assert json_file.exists()
        with open(json_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        assert "tradeoff_matrix" in raw_data
        assert "recommendations" in raw_data
        assert "comparison_summary" in raw_data

    def test_export_to_csv_headers_and_row_data(self, tmp_path: Path):
        """Verifies CSV export header schema and metric row values."""
        csv_file = tmp_path / "exports" / "benchmark_test.csv"
        result = evaluate_agentic_patterns(runs=2, mock=True, seed=44)

        export_pattern_benchmark_to_csv(result, str(csv_file))
        assert csv_file.exists()

        expected_headers = [
            "pattern_name",
            "total_runs",
            "mean_latency_s",
            "p50_latency_s",
            "p95_latency_s",
            "total_prompt_tokens",
            "total_completion_tokens",
            "total_tokens",
            "total_cost_usd",
            "cost_per_1k_requests",
            "error_recovery_success_rate",
            "mean_recovery_attempts",
            "mttr_seconds",
            "context_token_bloat_factor",
            "state_safety_score",
            "race_resistance_rate",
            "concurrency_safe",
        ]

        with open(csv_file, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header_row = next(reader)
            assert header_row == expected_headers

            rows = list(reader)
            assert len(rows) == 3
            pattern_names = [row[0] for row in rows]
            assert "Blackboard + Evaluator-Optimizer" in pattern_names
            assert "ReAct" in pattern_names
            assert "Hierarchical" in pattern_names


# ==============================================================================
# 7. STANDALONE CLI RUNNER TESTS
# ==============================================================================

class TestCliRunner:
    """Tests for compare_agentic_patterns CLI argument parsing and execution."""

    def test_cli_main_mock_execution(self):
        """Tests running main() with default mock arguments."""
        exit_code = compare_agentic_patterns.main(["--runs", "1", "--mock"])
        assert exit_code == 0

    def test_cli_main_with_model_override(self):
        """Tests running main() specifying an alternative model."""
        exit_code = compare_agentic_patterns.main([
            "--runs", "1",
            "--mock",
            "--model", "groq/llama-3.1-8b-instant",
        ])
        assert exit_code == 0

    def test_cli_main_with_file_exports(self, tmp_path: Path):
        """Tests running main() with both --export-json and --export-csv flags."""
        json_path = tmp_path / "cli_test.json"
        csv_path = tmp_path / "cli_test.csv"

        exit_code = compare_agentic_patterns.main([
            "--runs", "2",
            "--mock",
            "--export-json", str(json_path),
            "--export-csv", str(csv_path),
        ])
        assert exit_code == 0
        assert json_path.exists() and json_path.stat().st_size > 0
        assert csv_path.exists() and csv_path.stat().st_size > 0

    def test_cli_main_invalid_model_returns_exit_code_1(self):
        """Tests that specifying an invalid model returns exit code 1."""
        exit_code = compare_agentic_patterns.main([
            "--model", "unknown-fake-model-12345",
        ])
        assert exit_code == 1

    def test_cli_subprocess_execution(self):
        """Tests executing compare_agentic_patterns.py as a standalone subprocess."""
        cmd = [
            sys.executable,
            "compare_agentic_patterns.py",
            "--runs", "1",
            "--mock",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        assert res.returncode == 0
        assert "DEVAGENTS-AGI: AGENTIC DESIGN PATTERNS FORMAL COMPARATIVE EVALUATION" in res.stdout
        assert "Blackboard + Evaluator-Optimizer" in res.stdout
        assert "CORE COMPARATIVE PERFORMANCE & COST METRICS" in res.stdout
        assert "COMPREHENSIVE PATTERN TRADE-OFF MATRIX" in res.stdout
