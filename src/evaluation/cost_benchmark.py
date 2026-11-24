"""
Performance, Token, Cost, and Latency Evaluation Engine.

Executes comparative benchmarks across models (Groq and Gemini) and
prompt variances (ReAct, Few-Shot, Direct Schema). Measures token consumption,
calculated dollar costs, latency percentiles (P50, P90, P95), and success rates.
Supports deterministic mock execution and live LiteLLM inference, with exports
to standardized CSV and JSON formats.
"""

from __future__ import annotations

import csv
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from pydantic import BaseModel, ConfigDict, Field

from src.evaluation.pricing import (
    calculate_token_cost,
    get_model_pricing,
    get_supported_models,
    normalize_model_name,
)
from src.prompts.variance_manager import (
    PromptArchitecture,
    PromptPersona,
    PromptVarianceConfig,
    PromptVarianceManager,
)


class BenchmarkRun(BaseModel):
    """Record of a single benchmark trial."""
    model_config = ConfigDict(extra="allow")

    run_id: Optional[str] = Field(default=None, description="Optional run identifier")
    task_description: Optional[str] = Field(default=None, description="Optional task description alias")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of the benchmark run",
    )
    model: str = Field(..., description="Canonical model identifier")
    prompt_variance: str = Field(..., description="Prompt variance: react, few_shot, direct_schema")
    task_name: str = Field(default="architecture_generation", description="Benchmarked task name")
    prompt_tokens: int = Field(ge=0, description="Input/prompt token count")
    completion_tokens: int = Field(ge=0, description="Output/completion token count")
    total_tokens: int = Field(ge=0, description="Total tokens consumed")
    latency_s: float = Field(ge=0.0, description="Execution duration in seconds")
    cost_usd: float = Field(ge=0.0, description="Calculated dollar cost in USD")
    success: bool = Field(default=True, description="Whether the run succeeded without error")
    error: Optional[str] = Field(default=None, description="Error message if run failed")


class BenchmarkReport(BaseModel):
    """Aggregated benchmark report across models and prompt variances."""
    model_config = ConfigDict(extra="allow")

    runs: List[BenchmarkRun] = Field(default_factory=list, description="List of individual runs")
    summary_by_model: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Aggregated metrics grouped by model"
    )
    summary_by_variance: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Aggregated metrics grouped by prompt variance"
    )
    overall_summary: Dict[str, Any] = Field(
        default_factory=dict, description="Overall aggregated benchmark metrics"
    )
    summary_metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Summary metrics alias for overall summary"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Execution metadata and environment info"
    )

    def model_post_init(self, __context: Any) -> None:
        if not self.overall_summary and self.summary_metrics:
            self.overall_summary = dict(self.summary_metrics)
        elif not self.summary_metrics and self.overall_summary:
            self.summary_metrics = dict(self.overall_summary)

    def _get_metric(self, key: str, fallback: Any) -> Any:
        extra = self.__pydantic_extra__ or {}
        if key in extra and extra[key] is not None:
            return extra[key]
        if key in self.overall_summary:
            return self.overall_summary[key]
        if key in self.summary_metrics:
            return self.summary_metrics[key]
        return fallback

    @property
    def total_runs(self) -> int:
        return int(self._get_metric("total_runs", len(self.runs)))

    @property
    def successful_runs(self) -> int:
        return int(self._get_metric("successful_runs", sum(1 for r in self.runs if getattr(r, "success", True))))

    @property
    def failed_runs(self) -> int:
        return int(self._get_metric("failed_runs", sum(1 for r in self.runs if not getattr(r, "success", True))))

    @property
    def total_prompt_tokens(self) -> int:
        return int(self._get_metric("total_prompt_tokens", sum(getattr(r, "prompt_tokens", 0) for r in self.runs)))

    @property
    def total_completion_tokens(self) -> int:
        return int(self._get_metric("total_completion_tokens", sum(getattr(r, "completion_tokens", 0) for r in self.runs)))

    @property
    def total_tokens_consumed(self) -> int:
        return int(
            self._get_metric(
                "total_tokens_consumed",
                self._get_metric("total_tokens", self.total_prompt_tokens + self.total_completion_tokens),
            )
        )

    @property
    def total_evaluated_cost_usd(self) -> float:
        return float(
            self._get_metric(
                "total_evaluated_cost_usd",
                self._get_metric("total_cost_usd", sum(getattr(r, "cost_usd", 0.0) for r in self.runs)),
            )
        )

    @property
    def cost_per_1k_requests(self) -> float:
        return float(self._get_metric("cost_per_1k_requests", 0.0))

    @property
    def average_latency_s(self) -> float:
        return float(self._get_metric("average_latency_s", self._get_metric("avg_latency_s", 0.0)))


def calculate_percentile(values: Sequence[float], percentile: float) -> float:
    """
    Calculates a percentile using linear interpolation between nearest ranks.
    Safely handles empty sequences and small sample sizes (e.g. n=1, n=2).

    Args:
        values: Sequence of numeric values (e.g. latency measurements).
        percentile: Target percentile between 0.0 and 100.0.

    Returns:
        Calculated percentile rounded to 4 decimal places.
    """
    if not values:
        return 0.0

    sorted_vals = sorted(float(v) for v in values)
    n = len(sorted_vals)
    if n == 1:
        return round(sorted_vals[0], 4)

    clamped_p = max(0.0, min(100.0, float(percentile)))
    rank = (clamped_p / 100.0) * (n - 1)
    lower_idx = int(math.floor(rank))
    upper_idx = int(math.ceil(rank))

    if lower_idx == upper_idx:
        return round(sorted_vals[lower_idx], 4)

    weight = rank - lower_idx
    interpolated = sorted_vals[lower_idx] * (1.0 - weight) + sorted_vals[upper_idx] * weight
    return round(interpolated, 4)


def _compute_summary_metrics(runs: Sequence[BenchmarkRun]) -> Dict[str, Any]:
    """Computes comprehensive summary statistics for a given sequence of benchmark runs."""
    total_runs = len(runs)
    if total_runs == 0:
        return {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "success_rate": 0.0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "avg_prompt_tokens": 0.0,
            "avg_completion_tokens": 0.0,
            "avg_tokens": 0.0,
            "total_cost_usd": 0.0,
            "avg_cost_usd": 0.0,
            "cost_per_1k_requests": 0.0,
            "avg_latency_s": 0.0,
            "p50_latency_s": 0.0,
            "p90_latency_s": 0.0,
            "p95_latency_s": 0.0,
            "min_latency_s": 0.0,
            "max_latency_s": 0.0,
        }

    successful = [r for r in runs if r.success]
    failed = [r for r in runs if not r.success]
    total_prompt = sum(r.prompt_tokens for r in runs)
    total_completion = sum(r.completion_tokens for r in runs)
    total_tok = sum(r.total_tokens for r in runs)
    total_cost = round(sum(r.cost_usd for r in runs), 8)
    avg_cost = round(total_cost / total_runs, 8)
    cost_per_1k = round(avg_cost * 1000.0, 6)

    latencies = [r.latency_s for r in runs]
    avg_lat = round(sum(latencies) / total_runs, 4)
    p50 = calculate_percentile(latencies, 50.0)
    p90 = calculate_percentile(latencies, 90.0)
    p95 = calculate_percentile(latencies, 95.0)

    return {
        "total_runs": total_runs,
        "successful_runs": len(successful),
        "failed_runs": len(failed),
        "success_rate": round(len(successful) / total_runs, 4),
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_tokens": total_tok,
        "avg_prompt_tokens": round(total_prompt / total_runs, 2),
        "avg_completion_tokens": round(total_completion / total_runs, 2),
        "avg_tokens": round(total_tok / total_runs, 2),
        "total_cost_usd": total_cost,
        "avg_cost_usd": avg_cost,
        "cost_per_1k_requests": cost_per_1k,
        "avg_latency_s": avg_lat,
        "p50_latency_s": p50,
        "p90_latency_s": p90,
        "p95_latency_s": p95,
        "min_latency_s": round(min(latencies), 4) if latencies else 0.0,
        "max_latency_s": round(max(latencies), 4) if latencies else 0.0,
    }


def _get_prompt_for_variance(variance: str) -> str:
    """Builds an architecture generation prompt using PromptVarianceManager."""
    normalized_variance = variance.strip().lower()

    if normalized_variance == "react":
        arch = PromptArchitecture.REACT
    elif normalized_variance in ("few_shot", "fewshot"):
        arch = PromptArchitecture.FEW_SHOT
    else:
        arch = PromptArchitecture.DIRECT_SCHEMA

    config = PromptVarianceConfig(
        architecture=arch,
        persona=PromptPersona.PRAGMATIC_ARCHITECT,
        include_threat_modeling=False,
    )

    return PromptVarianceManager.build_architecture_prompt(
        project_name="E-Commerce Payment Service",
        description="High-throughput payment gateway client integrating Stripe and PayPal.",
        language="python",
        features=[
            "Process card charges",
            "Handle webhooks idempotently",
            "Refund transactions",
        ],
        acceptance_criteria=[
            "All payment transactions record unique idempotency keys",
            "Refunds validate original transaction status before processing",
            "Unit tests achieve 90%+ branch coverage",
        ],
        config=config,
    )


# Model latency factors relative to baseline
_MODEL_LATENCY_FACTORS: Dict[str, float] = {
    "groq/llama-3.1-8b-instant": 0.45,
    "gemini/gemini-2.0-flash": 0.50,
    "gemini/gemini-1.5-flash": 0.58,
    "groq/qwen/qwen3.8-27b": 0.85,
    "groq/llama-3.3-70b-versatile": 1.15,
    "gemini/gemini-1.5-pro": 1.45,
}


def _simulate_mock_run(
    model: str,
    variance: str,
    run_index: int,
    task_name: str = "architecture_generation",
) -> BenchmarkRun:
    """
    Synthesizes realistic, deterministic benchmark data reflecting the prompt variance
    characteristics and model pricing.
    """
    canonical_model = normalize_model_name(model)
    norm_variance = variance.strip().lower()
    prompt_text = _get_prompt_for_variance(norm_variance)
    base_prompt_tokens = max(100, len(prompt_text) // 4)

    # Variance-specific token dynamics:
    # - react: adds reasoning instructions (+50-70 tokens), produces reasoning thought chain (~300-360 tokens)
    # - few_shot: adds exemplar (+130-160 tokens), produces highly concise schema (~160-200 tokens)
    # - direct_schema: minimal prompt, standard schema completion (~220-250 tokens)
    if norm_variance == "react":
        prompt_tokens = base_prompt_tokens + 50 + (run_index * 2)
        completion_tokens = 320 + (run_index * 5)
        base_latency = 0.52
    elif norm_variance in ("few_shot", "fewshot"):
        prompt_tokens = base_prompt_tokens + 140 + (run_index * 2)
        completion_tokens = 180 + (run_index * 3)
        base_latency = 0.42
    else:  # direct_schema
        prompt_tokens = base_prompt_tokens + (run_index * 2)
        completion_tokens = 230 + (run_index * 4)
        base_latency = 0.35

    model_factor = _MODEL_LATENCY_FACTORS.get(canonical_model, 0.8)
    latency_s = round((base_latency * model_factor) + (run_index * 0.015), 4)
    total_tokens = prompt_tokens + completion_tokens
    cost_usd = calculate_token_cost(canonical_model, prompt_tokens, completion_tokens)

    return BenchmarkRun(
        model=canonical_model,
        prompt_variance=norm_variance,
        task_name=task_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        latency_s=latency_s,
        cost_usd=cost_usd,
        success=True,
        error=None,
    )


def _execute_live_run(
    model: str,
    variance: str,
    task_name: str = "architecture_generation",
) -> BenchmarkRun:
    """Executes a real LLM inference call via LiteLLM."""
    import litellm

    canonical_model = normalize_model_name(model)
    norm_variance = variance.strip().lower()
    prompt_text = _get_prompt_for_variance(norm_variance)

    start_time = time.perf_counter()
    try:
        response = litellm.completion(
            model=canonical_model,
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.1,
            max_tokens=1000,
        )
        latency_s = round(time.perf_counter() - start_time, 4)

        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or len(prompt_text) // 4)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 200)
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = calculate_token_cost(canonical_model, prompt_tokens, completion_tokens)

        return BenchmarkRun(
            model=canonical_model,
            prompt_variance=norm_variance,
            task_name=task_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_s=latency_s,
            cost_usd=cost_usd,
            success=True,
            error=None,
        )
    except Exception as exc:
        latency_s = round(time.perf_counter() - start_time, 4)
        return BenchmarkRun(
            model=canonical_model,
            prompt_variance=norm_variance,
            task_name=task_name,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_s=latency_s,
            cost_usd=0.0,
            success=False,
            error=str(exc),
        )


def export_to_csv(
    report_or_runs: Union[BenchmarkReport, Sequence[BenchmarkRun]],
    file_path: str,
) -> None:
    """
    Exports benchmark runs to flat CSV format with exact headers:
    timestamp,model,prompt_variance,task_name,prompt_tokens,completion_tokens,total_tokens,latency_s,cost_usd,success,error

    Args:
        report_or_runs: BenchmarkReport containing runs or Sequence of BenchmarkRun.
        file_path: Destination path for the CSV file.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(report_or_runs, BenchmarkReport):
        runs = report_or_runs.runs
    elif isinstance(report_or_runs, Sequence):
        runs = list(report_or_runs)
        if len(runs) == 0:
            raise ValueError("Cannot export empty benchmark runs")
    else:
        raise ValueError("Cannot export empty benchmark runs")

    fieldnames = [
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

    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for run in runs:
            writer.writerow({
                "timestamp": run.timestamp,
                "model": run.model,
                "prompt_variance": run.prompt_variance,
                "task_name": run.task_name,
                "prompt_tokens": run.prompt_tokens,
                "completion_tokens": run.completion_tokens,
                "total_tokens": run.total_tokens,
                "latency_s": run.latency_s,
                "cost_usd": f"{run.cost_usd:.8f}",
                "success": run.success,
                "error": run.error or "",
            })


def export_to_json(
    report_or_runs: Union[BenchmarkReport, Sequence[BenchmarkRun]],
    file_path: str,
) -> None:
    """
    Exports structured benchmark report with metadata, summary statistics, and run records.

    Args:
        report_or_runs: BenchmarkReport to export or Sequence of BenchmarkRun.
        file_path: Destination path for the JSON file.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(report_or_runs, BenchmarkReport):
        report = report_or_runs
        data = report.model_dump()
        summary = report.overall_summary or report.summary_metrics or {}
        data["overall_summary"] = summary
        data["summary_metrics"] = summary
    elif isinstance(report_or_runs, Sequence):
        runs = list(report_or_runs)
        if len(runs) == 0:
            raise ValueError("Cannot export empty benchmark runs")
        summary = _compute_summary_metrics(runs)
        data = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_runs_count": len(runs),
            },
            "summary_metrics": summary,
            "overall_summary": summary,
            "summary_by_model": {},
            "summary_by_variance": {},
            "runs": [r.model_dump() for r in runs],
        }
    else:
        raise ValueError("Cannot export empty benchmark runs")

    with open(path, mode="w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def run_cost_benchmark(
    models: Optional[Sequence[str]] = None,
    prompt_variances: Optional[Sequence[str]] = None,
    mock: bool = True,
    export_csv: Optional[str] = None,
    export_json: Optional[str] = None,
    runs_per_variance: int = 3,
    runs: Optional[int] = None,
) -> BenchmarkReport:
    """
    Executes the performance, token, cost, and latency evaluation benchmark suite.

    Args:
        models: List of model names or aliases. Defaults to all supported models.
        prompt_variances: List of prompt variance names ("react", "few_shot", "direct_schema").
                          Defaults to all three.
        mock: If True, runs deterministic offline mock benchmarks. If False, queries live models via LiteLLM.
        export_csv: Optional file path to export CSV report.
        export_json: Optional file path to export JSON report.
        runs_per_variance: Number of benchmark repetitions per model/variance pair (must be >= 1).
        runs: Optional alias for runs_per_variance.

    Returns:
        BenchmarkReport containing all runs, model summaries, variance summaries, and overall metrics.
    """
    if runs is not None:
        runs_per_variance = runs

    if runs_per_variance < 1:
        raise ValueError(f"runs_per_variance must be >= 1, got {runs_per_variance}")

    # Resolve target models
    target_models = [normalize_model_name(m) for m in models] if models else get_supported_models()

    # Resolve target prompt variances
    valid_variances = ["react", "few_shot", "direct_schema"]
    if prompt_variances:
        target_variances = []
        for v in prompt_variances:
            nv = v.strip().lower()
            if nv in ("fewshot", "few_shot"):
                target_variances.append("few_shot")
            elif nv in valid_variances:
                target_variances.append(nv)
            else:
                raise ValueError(
                    f"Unknown prompt variance: '{v}'. Valid variances: {valid_variances}"
                )
    else:
        target_variances = valid_variances

    runs: List[BenchmarkRun] = []

    for model in target_models:
        for variance in target_variances:
            for r in range(runs_per_variance):
                if mock:
                    run_record = _simulate_mock_run(model, variance, r)
                else:
                    run_record = _execute_live_run(model, variance)
                runs.append(run_record)

    # Compute summaries
    summary_by_model: Dict[str, Dict[str, Any]] = {}
    for model in target_models:
        model_runs = [r for r in runs if r.model == model]
        summary_by_model[model] = _compute_summary_metrics(model_runs)

    summary_by_variance: Dict[str, Dict[str, Any]] = {}
    for variance in target_variances:
        var_runs = [r for r in runs if r.prompt_variance == variance]
        summary_by_variance[variance] = _compute_summary_metrics(var_runs)

    overall_summary = _compute_summary_metrics(runs)

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mock_mode": mock,
        "runs_per_variance": runs_per_variance,
        "models_evaluated": target_models,
        "variances_evaluated": target_variances,
        "total_runs_count": len(runs),
    }

    report = BenchmarkReport(
        runs=runs,
        summary_by_model=summary_by_model,
        summary_by_variance=summary_by_variance,
        overall_summary=overall_summary,
        summary_metrics=overall_summary,
        metadata=metadata,
    )

    if export_csv:
        export_to_csv(report, export_csv)

    if export_json:
        export_to_json(report, export_json)

    return report
