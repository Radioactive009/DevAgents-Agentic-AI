"""
Unit and Integration Tests for Performance, Cost & Latency Evaluation Suite (Requirement 10).

Validates:
- Model pricing catalog rates and token cost computation math.
- Model name normalization and alias resolution.
- Error handling on invalid inputs (negative tokens, unsupported models).
- Percentile calculations (P50, P90, P95) across diverse sample sizes.
- BenchmarkRun and BenchmarkReport Pydantic data schemas.
- Deterministic mock benchmark execution across models and prompt variances.
- Prompt variance dynamics (ReAct reasoning vs Few-Shot exemplars vs Direct Schema).
- CSV export formatting and exact header conformity.
- JSON export structured schema and summary aggregations.
- CLI argument parsing and execution harness.
"""

import csv
import json
import math
import subprocess
import sys
from pathlib import Path
import pytest

from src.evaluation.cost_benchmark import (
    BenchmarkReport,
    BenchmarkRun,
    calculate_percentile,
    export_to_csv,
    export_to_json,
    run_cost_benchmark,
)
from src.evaluation.pricing import (
    MODEL_PRICING_CATALOG,
    calculate_token_cost,
    get_model_pricing,
    get_supported_models,
    normalize_model_name,
)
import benchmark_performance_cost


# =====================================================================
# 1. PRICING CATALOG & NORMALIZATION TESTS
# =====================================================================

class TestModelPricingCatalog:
    """Tests for model pricing catalog rates and model name normalization."""

    def test_pricing_catalog_contains_all_target_models(self):
        """Verifies that all 6 required target models exist in the catalog."""
        expected_models = {
            "groq/qwen/qwen3.8-27b",
            "groq/llama-3.3-70b-versatile",
            "groq/llama-3.1-8b-instant",
            "gemini/gemini-1.5-flash",
            "gemini/gemini-1.5-pro",
            "gemini/gemini-2.0-flash",
        }
        supported = set(get_supported_models())
        assert expected_models.issubset(supported)

    def test_pricing_catalog_rates_match_specification(self):
        """Verifies exact pricing rates per million tokens and per token."""
        # groq/qwen/qwen3.8-27b: Input $0.80 / 1M, Output $4.00 / 1M
        qwen = get_model_pricing("groq/qwen/qwen3.8-27b")
        assert qwen.input_cost_per_million == 0.80
        assert qwen.output_cost_per_million == 4.00
        assert math.isclose(qwen.input_cost_per_token, 0.0000008, rel_tol=1e-9)
        assert math.isclose(qwen.output_cost_per_token, 0.000004, rel_tol=1e-9)

        # groq/llama-3.3-70b-versatile: Input $0.59 / 1M, Output $0.79 / 1M
        llama70 = get_model_pricing("groq/llama-3.3-70b-versatile")
        assert llama70.input_cost_per_million == 0.59
        assert llama70.output_cost_per_million == 0.79
        assert math.isclose(llama70.input_cost_per_token, 0.00000059, rel_tol=1e-9)
        assert math.isclose(llama70.output_cost_per_token, 0.00000079, rel_tol=1e-9)

        # groq/llama-3.1-8b-instant: Input $0.05 / 1M, Output $0.08 / 1M
        llama8 = get_model_pricing("groq/llama-3.1-8b-instant")
        assert llama8.input_cost_per_million == 0.05
        assert llama8.output_cost_per_million == 0.08
        assert math.isclose(llama8.input_cost_per_token, 0.00000005, rel_tol=1e-9)
        assert math.isclose(llama8.output_cost_per_token, 0.00000008, rel_tol=1e-9)

        # gemini/gemini-1.5-flash: Input $0.075 / 1M, Output $0.30 / 1M
        flash15 = get_model_pricing("gemini/gemini-1.5-flash")
        assert flash15.input_cost_per_million == 0.075
        assert flash15.output_cost_per_million == 0.30
        assert math.isclose(flash15.input_cost_per_token, 0.000000075, rel_tol=1e-9)
        assert math.isclose(flash15.output_cost_per_token, 0.0000003, rel_tol=1e-9)

        # gemini/gemini-1.5-pro: Input $1.25 / 1M, Output $5.00 / 1M
        pro15 = get_model_pricing("gemini/gemini-1.5-pro")
        assert pro15.input_cost_per_million == 1.25
        assert pro15.output_cost_per_million == 5.00
        assert math.isclose(pro15.input_cost_per_token, 0.00000125, rel_tol=1e-9)
        assert math.isclose(pro15.output_cost_per_token, 0.000005, rel_tol=1e-9)

        # gemini/gemini-2.0-flash: Input $0.10 / 1M, Output $0.40 / 1M
        flash20 = get_model_pricing("gemini/gemini-2.0-flash")
        assert flash20.input_cost_per_million == 0.10
        assert flash20.output_cost_per_million == 0.40
        assert math.isclose(flash20.input_cost_per_token, 0.0000001, rel_tol=1e-9)
        assert math.isclose(flash20.output_cost_per_token, 0.0000004, rel_tol=1e-9)

    @pytest.mark.parametrize(
        "alias,expected",
        [
            ("qwen3.8-27b", "groq/qwen/qwen3.8-27b"),
            ("qwen/qwen3.8-27b", "groq/qwen/qwen3.8-27b"),
            ("QWEN3.8-27B", "groq/qwen/qwen3.8-27b"),
            ("llama-3.3-70b-versatile", "groq/llama-3.3-70b-versatile"),
            ("llama-3.3-70b", "groq/llama-3.3-70b-versatile"),
            ("llama-3.1-8b-instant", "groq/llama-3.1-8b-instant"),
            ("llama-3.1-8b", "groq/llama-3.1-8b-instant"),
            ("gemini-1.5-flash", "gemini/gemini-1.5-flash"),
            ("models/gemini-1.5-flash", "gemini/gemini-1.5-flash"),
            ("gemini-1.5-pro", "gemini/gemini-1.5-pro"),
            ("gemini-2.0-flash", "gemini/gemini-2.0-flash"),
            ("gemini-2.0", "gemini/gemini-2.0-flash"),
        ],
    )
    def test_normalize_model_name_aliases(self, alias, expected):
        """Verifies that short names and provider aliases resolve to canonical names."""
        assert normalize_model_name(alias) == expected

    def test_normalize_unknown_model_raises_value_error(self):
        """Verifies that unknown model names raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported model"):
            normalize_model_name("gpt-4o-unknown")

    def test_normalize_empty_model_name_raises_value_error(self):
        """Verifies that empty string or non-string model raises ValueError."""
        with pytest.raises(ValueError, match="non-empty string"):
            normalize_model_name("")


# =====================================================================
# 2. TOKEN COST CALCULATION MATH TESTS
# =====================================================================

class TestTokenCostCalculation:
    """Tests for exact token cost computation and error handling."""

    def test_calculate_token_cost_exact_values(self):
        """Tests precise floating point dollar cost calculations."""
        # Qwen 27B: 1,000 prompt tokens + 500 completion tokens
        # = (1000 * 0.80 + 500 * 4.00) / 1,000,000 = (800 + 2000) / 1,000,000 = 0.0028
        cost = calculate_token_cost("groq/qwen/qwen3.8-27b", 1000, 500)
        assert cost == 0.0028

        # LLaMA 3.1 8B: 10,000 prompt tokens + 2,000 completion tokens
        # = (10000 * 0.05 + 2000 * 0.08) / 1,000,000 = (500 + 160) / 1,000,000 = 0.00066
        cost = calculate_token_cost("llama-3.1-8b-instant", 10000, 2000)
        assert cost == 0.00066

        # Gemini 1.5 Flash: 1,000,000 prompt + 1,000,000 completion = 0.075 + 0.30 = 0.375
        cost = calculate_token_cost("gemini-1.5-flash", 1_000_000, 1_000_000)
        assert cost == 0.375

        # Gemini 1.5 Pro: 100 prompt + 100 completion
        # = (100 * 1.25 + 100 * 5.00) / 1,000,000 = 625 / 1,000,000 = 0.000625
        cost = calculate_token_cost("gemini-1.5-pro", 100, 100)
        assert cost == 0.000625

    def test_calculate_token_cost_zero_tokens(self):
        """Verifies that zero tokens produces exactly $0.00 cost."""
        cost = calculate_token_cost("groq/qwen/qwen3.8-27b", 0, 0)
        assert cost == 0.0

    @pytest.mark.parametrize(
        "prompt_tokens,completion_tokens",
        [
            (-1, 100),
            (100, -5),
            (-10, -10),
        ],
    )
    def test_calculate_token_cost_negative_tokens_raises_error(self, prompt_tokens, completion_tokens):
        """Verifies that negative token counts raise ValueError."""
        with pytest.raises(ValueError, match="non-negative integer"):
            calculate_token_cost("groq/qwen/qwen3.8-27b", prompt_tokens, completion_tokens)

    @pytest.mark.parametrize(
        "prompt_tokens,completion_tokens",
        [
            ("100", 50),
            (50, 12.5),
        ],
    )
    def test_calculate_token_cost_non_integer_tokens_raises_error(self, prompt_tokens, completion_tokens):
        """Verifies that non-integer token counts raise ValueError."""
        with pytest.raises(ValueError, match="non-negative integer"):
            calculate_token_cost("groq/qwen/qwen3.8-27b", prompt_tokens, completion_tokens)


# =====================================================================
# 3. PERCENTILE CALCULATION TESTS
# =====================================================================

class TestPercentileCalculations:
    """Tests for robust percentile calculation (P50, P90, P95)."""

    def test_percentile_empty_sequence(self):
        """Empty sequence returns 0.0 safely."""
        assert calculate_percentile([], 50.0) == 0.0
        assert calculate_percentile([], 95.0) == 0.0

    def test_percentile_single_value(self):
        """Single-element sequence returns that element."""
        assert calculate_percentile([0.45], 50.0) == 0.45
        assert calculate_percentile([0.45], 90.0) == 0.45
        assert calculate_percentile([0.45], 95.0) == 0.45

    def test_percentile_two_values(self):
        """Two values use linear interpolation."""
        # P50 between 1.0 and 2.0 = 1.5
        assert calculate_percentile([1.0, 2.0], 50.0) == 1.5
        # P90 between 1.0 and 2.0 = 1.0*0.1 + 2.0*0.9 = 1.9
        assert calculate_percentile([1.0, 2.0], 90.0) == 1.9

    def test_percentile_known_distributions(self):
        """Tests known values for P50, P90, P95 on larger lists."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        # P50 (median) = 3.0
        assert calculate_percentile(values, 50.0) == 3.0
        # P90: rank = 0.9 * 4 = 3.6 -> values[3]*0.4 + values[4]*0.6 = 4.0*0.4 + 5.0*0.6 = 4.6
        assert calculate_percentile(values, 90.0) == 4.6
        # P95: rank = 0.95 * 4 = 3.8 -> 4.0*0.2 + 5.0*0.8 = 4.8
        assert calculate_percentile(values, 95.0) == 4.8

    def test_percentile_boundary_clamping(self):
        """Percentiles are clamped between 0 and 100."""
        values = [10.0, 20.0, 30.0]
        assert calculate_percentile(values, 0.0) == 10.0
        assert calculate_percentile(values, 100.0) == 30.0


# =====================================================================
# 4. BENCHMARK RUN & REPORT SCHEMA TESTS
# =====================================================================

class TestBenchmarkSchemas:
    """Tests Pydantic validation of BenchmarkRun and BenchmarkReport."""

    def test_valid_benchmark_run_creation(self):
        """Verifies creating a valid BenchmarkRun instance."""
        run = BenchmarkRun(
            model="groq/qwen/qwen3.8-27b",
            prompt_variance="react",
            task_name="test_task",
            prompt_tokens=200,
            completion_tokens=150,
            total_tokens=350,
            latency_s=0.45,
            cost_usd=0.00076,
            success=True,
        )
        assert run.model == "groq/qwen/qwen3.8-27b"
        assert run.total_tokens == 350
        assert run.success is True
        assert run.error is None
        assert run.timestamp is not None

    def test_benchmark_run_rejects_negative_tokens(self):
        """Verifies that negative tokens raise Pydantic ValidationError."""
        with pytest.raises(Exception):
            BenchmarkRun(
                model="groq/qwen/qwen3.8-27b",
                prompt_variance="react",
                prompt_tokens=-10,
                completion_tokens=50,
                total_tokens=40,
                latency_s=0.2,
                cost_usd=0.01,
            )


# =====================================================================
# 5. CORE BENCHMARK EXECUTION & PROMPT DYNAMICS TESTS
# =====================================================================

class TestBenchmarkExecution:
    """Tests for run_cost_benchmark in mock mode and prompt variance dynamics."""

    def test_run_cost_benchmark_mock_single_model(self):
        """Executes mock benchmark on one model and validates counts and summaries."""
        report = run_cost_benchmark(
            models=["groq/qwen/qwen3.8-27b"],
            prompt_variances=["react", "few_shot", "direct_schema"],
            mock=True,
            runs_per_variance=2,
        )
        # 1 model * 3 variances * 2 runs = 6 runs
        assert len(report.runs) == 6
        assert report.overall_summary["total_runs"] == 6
        assert report.overall_summary["success_rate"] == 1.0
        assert report.overall_summary["total_cost_usd"] > 0.0
        assert "groq/qwen/qwen3.8-27b" in report.summary_by_model
        assert "react" in report.summary_by_variance
        assert "few_shot" in report.summary_by_variance
        assert "direct_schema" in report.summary_by_variance

    def test_prompt_variance_token_dynamics(self):
        """
        Validates prompt variance behavioral characteristics:
        - FEW_SHOT has highest prompt tokens (due to exemplar injection).
        - REACT has highest completion tokens (due to reasoning thought chain).
        - DIRECT_SCHEMA has lowest prompt tokens and latency.
        """
        report = run_cost_benchmark(
            models=["groq/llama-3.1-8b-instant"],
            prompt_variances=["react", "few_shot", "direct_schema"],
            mock=True,
            runs_per_variance=3,
        )
        var_summary = report.summary_by_variance

        react_prompt_tok = var_summary["react"]["avg_prompt_tokens"]
        few_shot_prompt_tok = var_summary["few_shot"]["avg_prompt_tokens"]
        direct_prompt_tok = var_summary["direct_schema"]["avg_prompt_tokens"]

        react_compl_tok = var_summary["react"]["avg_completion_tokens"]
        few_shot_compl_tok = var_summary["few_shot"]["avg_completion_tokens"]
        direct_compl_tok = var_summary["direct_schema"]["avg_completion_tokens"]

        # Prompt token hierarchy: few_shot > react > direct_schema
        assert few_shot_prompt_tok > react_prompt_tok
        assert react_prompt_tok > direct_prompt_tok

        # Completion token hierarchy: react has reasoning chain overhead
        assert react_compl_tok > few_shot_compl_tok
        assert react_compl_tok > direct_compl_tok

        # Latency hierarchy: direct_schema is fastest
        assert var_summary["direct_schema"]["avg_latency_s"] < var_summary["react"]["avg_latency_s"]

    def test_run_cost_benchmark_all_supported_models(self):
        """Runs mock benchmark on all 6 supported models."""
        report = run_cost_benchmark(mock=True, runs_per_variance=1)
        assert len(report.runs) == 18  # 6 models * 3 variances * 1 run
        assert len(report.summary_by_model) == 6
        assert report.overall_summary["successful_runs"] == 18

    def test_run_cost_benchmark_invalid_variance_raises_error(self):
        """Unknown prompt variance raises ValueError."""
        with pytest.raises(ValueError, match="Unknown prompt variance"):
            run_cost_benchmark(prompt_variances=["invalid_var"], mock=True)

    def test_run_cost_benchmark_invalid_runs_count_raises_error(self):
        """runs_per_variance < 1 raises ValueError."""
        with pytest.raises(ValueError, match="runs_per_variance must be >= 1"):
            run_cost_benchmark(runs_per_variance=0, mock=True)


# =====================================================================
# 6. CSV & JSON EXPORT TESTS
# =====================================================================

class TestBenchmarkExports:
    """Tests CSV and JSON export formats and exact schemas."""

    def test_export_to_csv_headers_and_data(self, tmp_path):
        """Verifies exact CSV header matching Requirement 10 specification."""
        csv_file = tmp_path / "results.csv"
        report = run_cost_benchmark(
            models=["groq/qwen/qwen3.8-27b"],
            prompt_variances=["react"],
            mock=True,
            runs_per_variance=2,
            export_csv=str(csv_file),
        )
        assert csv_file.exists()

        expected_headers = [
            "timestamp",
            "model",
            "prompt_variance",
            "task_name",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "latency_s",
            "cost_usd",
            "success",
            "error",
        ]

        with open(csv_file, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header_row = next(reader)
            assert header_row == expected_headers

            rows = list(reader)
            assert len(rows) == 2
            # Check row fields
            assert rows[0][1] == "groq/qwen/qwen3.8-27b"
            assert rows[0][2] == "react"
            assert rows[0][9] == "True"

    def test_export_to_json_structure_and_metadata(self, tmp_path):
        """Verifies JSON schema contains metadata, summaries, and individual runs."""
        json_file = tmp_path / "results.json"
        report = run_cost_benchmark(
            models=["gemini/gemini-1.5-flash"],
            prompt_variances=["direct_schema"],
            mock=True,
            runs_per_variance=2,
            export_json=str(json_file),
        )
        assert json_file.exists()

        with open(json_file, mode="r", encoding="utf-8") as f:
            data = json.load(f)

        assert "runs" in data
        assert "summary_by_model" in data
        assert "summary_by_variance" in data
        assert "overall_summary" in data
        assert "metadata" in data

        assert len(data["runs"]) == 2
        assert data["metadata"]["mock_mode"] is True
        assert data["overall_summary"]["p50_latency_s"] > 0.0
        assert data["overall_summary"]["total_cost_usd"] > 0.0


# =====================================================================
# 7. CLI EXECUTION & ARGUMENT PARSING TESTS
# =====================================================================

class TestBenchmarkCliHarness:
    """Tests command-line interface execution and argument parsing."""

    def test_cli_main_mock_execution(self):
        """Tests running main() with mock flag and single run."""
        exit_code = benchmark_performance_cost.main(
            ["--mock", "--models", "llama-3.1-8b-instant", "--runs", "1"]
        )
        assert exit_code == 0

    def test_cli_main_with_file_exports(self, tmp_path):
        """Tests running main() producing both CSV and JSON exports."""
        csv_path = tmp_path / "cli_results.csv"
        json_path = tmp_path / "cli_results.json"

        exit_code = benchmark_performance_cost.main(
            [
                "--mock",
                "--models", "gemini-2.0-flash",
                "--variances", "react,few_shot",
                "--runs", "1",
                "--export-csv", str(csv_path),
                "--export-json", str(json_path),
            ]
        )
        assert exit_code == 0
        assert csv_path.exists()
        assert json_path.exists()

    def test_cli_main_invalid_model_fails_gracefully(self):
        """Tests that invalid model name returns exit code 1."""
        exit_code = benchmark_performance_cost.main(
            ["--mock", "--models", "invalid-fake-model", "--runs", "1"]
        )
        assert exit_code == 1

    def test_cli_subprocess_execution(self):
        """Tests executing the CLI script as a standalone subprocess."""
        cmd = [
            sys.executable,
            "benchmark_performance_cost.py",
            "--mock",
            "--models", "qwen3.8-27b",
            "--runs", "1",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        assert result.returncode == 0
        assert "DEVAGENTS-AGI: PERFORMANCE, COST & LATENCY EVALUATION SUITE" in result.stdout
        assert "groq/qwen/qwen3.8-27b" in result.stdout


# =====================================================================
# 8. ITERATION 2 INTERFACE & ERGONOMICS ENHANCEMENTS
# =====================================================================

class TestIteration2InterfaceEnhancements:
    """Validates backward-compatible interface updates identified by Challenger 1."""

    def test_run_cost_benchmark_with_runs_keyword_argument(self):
        """Verifies run_cost_benchmark accepts runs keyword argument alias."""
        report = run_cost_benchmark(
            models=["groq/llama-3.1-8b-instant"],
            prompt_variances=["react"],
            mock=True,
            runs=2,
        )
        assert len(report.runs) == 2
        assert report.total_runs == 2

    def test_benchmark_report_convenience_properties_populated(self):
        """Verifies top-level @property accessors on BenchmarkReport forwarding to overall_summary."""
        report = run_cost_benchmark(
            models=["groq/llama-3.1-8b-instant", "gemini/gemini-1.5-flash"],
            prompt_variances=["react"],
            mock=True,
            runs_per_variance=2,
        )
        assert report.total_runs == 4
        assert report.successful_runs == 4
        assert report.failed_runs == 0
        assert report.total_prompt_tokens > 0
        assert report.total_completion_tokens > 0
        assert report.total_tokens_consumed == report.total_prompt_tokens + report.total_completion_tokens
        assert report.total_evaluated_cost_usd > 0.0
        assert report.cost_per_1k_requests > 0.0
        assert 0.0 <= report.average_latency_s <= 5.0

    def test_benchmark_report_convenience_properties_computed_fallback(self):
        """Verifies top-level @property accessors compute valid fallback values from runs when overall_summary is empty."""
        run1 = BenchmarkRun(
            run_id="run-1",
            model="groq/llama-3.1-8b-instant",
            prompt_variance="react",
            task_name="test_arch",
            task_description="Custom arch task",
            prompt_tokens=120,
            completion_tokens=80,
            total_tokens=200,
            latency_s=0.35,
            cost_usd=0.000012,
            success=True,
        )
        run2 = BenchmarkRun(
            run_id="run-2",
            model="gemini/gemini-1.5-flash",
            prompt_variance="react",
            task_name="test_arch",
            prompt_tokens=150,
            completion_tokens=50,
            total_tokens=200,
            latency_s=0.45,
            cost_usd=0.000026,
            success=False,
            error="Simulated failure",
        )
        report = BenchmarkReport(runs=[run1, run2])
        assert report.total_runs == 2
        assert report.successful_runs == 1
        assert report.failed_runs == 1
        assert report.total_prompt_tokens == 270
        assert report.total_completion_tokens == 130
        assert report.total_tokens_consumed == 400
        assert math.isclose(report.total_evaluated_cost_usd, 0.000038, rel_tol=1e-6)
        assert report.cost_per_1k_requests == 0.0
        assert report.average_latency_s == 0.0

    def test_benchmark_run_optional_fields(self):
        """Verifies BenchmarkRun schema supports optional run_id and task_description fields."""
        run = BenchmarkRun(
            run_id="trial-007",
            task_description="High concurrency stress run",
            model="groq/llama-3.3-70b-versatile",
            prompt_variance="few_shot",
            prompt_tokens=500,
            completion_tokens=200,
            total_tokens=700,
            latency_s=0.85,
            cost_usd=0.00045,
        )
        assert run.run_id == "trial-007"
        assert run.task_description == "High concurrency stress run"

    def test_export_to_csv_with_runs_sequence(self, tmp_path: Path):
        """Verifies export_to_csv accepts a raw Sequence[BenchmarkRun]."""
        run = BenchmarkRun(
            run_id="seq-1",
            model="groq/llama-3.1-8b-instant",
            prompt_variance="react",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            latency_s=0.2,
            cost_usd=0.00001,
        )
        csv_path = tmp_path / "seq_export.csv"
        export_to_csv([run], str(csv_path))
        assert csv_path.exists()
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["model"] == "groq/llama-3.1-8b-instant"

    def test_export_to_csv_empty_sequence_raises_value_error(self, tmp_path: Path):
        """Verifies export_to_csv raises ValueError when given an empty sequence of runs."""
        csv_path = tmp_path / "empty_seq.csv"
        with pytest.raises(ValueError, match="Cannot export empty benchmark runs"):
            export_to_csv([], str(csv_path))

    def test_export_to_json_with_runs_sequence(self, tmp_path: Path):
        """Verifies export_to_json accepts a raw Sequence[BenchmarkRun] and writes summary_metrics."""
        run = BenchmarkRun(
            run_id="seq-json-1",
            model="gemini/gemini-2.0-flash",
            prompt_variance="direct_schema",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            latency_s=0.25,
            cost_usd=0.00006,
        )
        json_path = tmp_path / "seq_export.json"
        export_to_json([run], str(json_path))
        assert json_path.exists()
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "overall_summary" in data
            assert "summary_metrics" in data
            assert data["summary_metrics"]["total_runs"] == 1
            assert len(data["runs"]) == 1

    def test_export_to_json_empty_sequence_raises_value_error(self, tmp_path: Path):
        """Verifies export_to_json raises ValueError when given an empty sequence of runs."""
        json_path = tmp_path / "empty_seq.json"
        with pytest.raises(ValueError, match="Cannot export empty benchmark runs"):
            export_to_json([], str(json_path))

    def test_export_to_json_contains_both_overall_summary_and_summary_metrics(self, tmp_path: Path):
        """Verifies JSON export of BenchmarkReport includes both overall_summary and summary_metrics keys."""
        json_path = tmp_path / "dual_summary.json"
        report = run_cost_benchmark(
            models=["groq/llama-3.1-8b-instant"],
            prompt_variances=["react"],
            mock=True,
            runs_per_variance=1,
            export_json=str(json_path),
        )
        assert json_path.exists()
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "overall_summary" in data
            assert "summary_metrics" in data
            assert data["overall_summary"] == data["summary_metrics"]
