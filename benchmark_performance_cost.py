#!/usr/bin/env python3
"""
CLI Benchmark Runner for LLM Performance, Cost, Token, and Latency Evaluation.

Benchmarks Groq and Google Gemini models across prompt variances (ReAct, Few-Shot, Direct Schema).
Supports offline deterministic mock benchmarking and live LiteLLM queries, exporting structured
reports to CSV and JSON formats.

Usage Examples:
    # Quick mock run with all models and variances
    python benchmark_performance_cost.py --mock

    # Specific models and variances with exports
    python benchmark_performance_cost.py --models qwen3.8-27b,gemini-1.5-flash \
        --variances react,few_shot --runs 3 \
        --export-csv logs/benchmark_results.csv --export-json logs/benchmark_results.json

    # Live benchmarking against active API endpoints
    python benchmark_performance_cost.py --live --models groq/llama-3.1-8b-instant
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from src.evaluation.cost_benchmark import (
    BenchmarkReport,
    run_cost_benchmark,
)
from src.evaluation.pricing import get_supported_models


def parse_comma_separated_list(items: Optional[List[str]]) -> Optional[List[str]]:
    """Splits items that may be comma-separated or space-separated into a clean list."""
    if not items:
        return None
    result = []
    for item in items:
        for part in item.split(","):
            cleaned = part.strip()
            if cleaned:
                result.append(cleaned)
    return result if result else None


def print_banner() -> None:
    """Prints the evaluation suite banner."""
    print("=" * 80)
    print("   DEVAGENTS-AGI: PERFORMANCE, COST & LATENCY EVALUATION SUITE (REQ 10)")
    print("=" * 80)


def print_model_table(report: BenchmarkReport) -> None:
    """Prints summary table grouped by model."""
    print("\n--- PERFORMANCE & COST SUMMARY BY MODEL ---")
    header = (
        f"{'Model':<30} | {'Runs':>4} | {'Success':>7} | {'Avg Lat':>8} | "
        f"{'P50 (s)':>8} | {'P95 (s)':>8} | {'Total ($)':>10} | {'Cost/1k ($)':>11}"
    )
    print(header)
    print("-" * len(header))

    for model, stats in report.summary_by_model.items():
        success_pct = f"{stats['success_rate'] * 100:.1f}%"
        avg_lat = f"{stats['avg_latency_s']:.3f}s"
        p50_lat = f"{stats['p50_latency_s']:.3f}s"
        p95_lat = f"{stats['p95_latency_s']:.3f}s"
        total_cost = f"${stats['total_cost_usd']:.6f}"
        cost_1k = f"${stats['cost_per_1k_requests']:.4f}"

        print(
            f"{model:<30} | {stats['total_runs']:>4} | {success_pct:>7} | {avg_lat:>8} | "
            f"{p50_lat:>8} | {p95_lat:>8} | {total_cost:>10} | {cost_1k:>11}"
        )


def print_variance_table(report: BenchmarkReport) -> None:
    """Prints summary table grouped by prompt variance."""
    print("\n--- PROMPT VARIANCE COMPARATIVE SUMMARY ---")
    header = (
        f"{'Prompt Variance':<16} | {'Runs':>4} | {'Avg Prompt Tok':>14} | "
        f"{'Avg Compl Tok':>13} | {'Avg Latency':>11} | {'Avg Cost ($)':>13}"
    )
    print(header)
    print("-" * len(header))

    for variance, stats in report.summary_by_variance.items():
        avg_prompt = f"{stats['avg_prompt_tokens']:.1f}"
        avg_compl = f"{stats['avg_completion_tokens']:.1f}"
        avg_lat = f"{stats['avg_latency_s']:.3f}s"
        avg_cost = f"${stats['avg_cost_usd']:.6f}"

        print(
            f"{variance:<16} | {stats['total_runs']:>4} | {avg_prompt:>14} | "
            f"{avg_compl:>13} | {avg_lat:>11} | {avg_cost:>13}"
        )


def print_overall_summary(report: BenchmarkReport) -> None:
    """Prints the global summary metrics."""
    s = report.overall_summary
    print("\n--- GLOBAL BENCHMARK TOTALS ---")
    print(f"  Total Runs Executed:       {s['total_runs']}")
    print(f"  Successful Runs:           {s['successful_runs']} ({s['success_rate'] * 100:.1f}%)")
    print(f"  Total Prompt Tokens:       {s['total_prompt_tokens']:,}")
    print(f"  Total Completion Tokens:   {s['total_completion_tokens']:,}")
    print(f"  Total Tokens Consumed:     {s['total_tokens']:,}")
    print(f"  Total Evaluated Cost:      ${s['total_cost_usd']:.6f} USD")
    print(f"  Avg Cost per Request:      ${s['avg_cost_usd']:.6f} USD")
    print(f"  Cost per 1,000 Requests:   ${s['cost_per_1k_requests']:.4f} USD")
    print(f"  Average Latency:           {s['avg_latency_s']:.3f}s (P50: {s['p50_latency_s']:.3f}s, P90: {s['p90_latency_s']:.3f}s, P95: {s['p95_latency_s']:.3f}s)")
    print("=" * 80)


def build_parser() -> argparse.ArgumentParser:
    """Constructs the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Benchmark LLM performance, latency, tokens, and cost across prompt variances.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--models",
        nargs="*",
        help=(
            "Model names or aliases to benchmark (e.g. qwen3.8-27b, gemini-1.5-flash). "
            f"Defaults to all supported models: {', '.join(get_supported_models())}"
        ),
    )
    parser.add_argument(
        "--variances",
        nargs="*",
        help="Prompt variances to evaluate ('react', 'few_shot', 'direct_schema'). Defaults to all.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Repetitions per model and variance combination (default: 3).",
    )
    parser.add_argument(
        "--mock",
        dest="mock",
        action="store_true",
        default=True,
        help="Run deterministic offline benchmark without live API calls (default: True).",
    )
    parser.add_argument(
        "--live",
        dest="mock",
        action="store_false",
        help="Run live inference calls against configured model provider APIs.",
    )
    parser.add_argument(
        "--export-csv",
        type=str,
        default=None,
        help="File path to save CSV benchmark results (e.g. logs/benchmark_results.csv).",
    )
    parser.add_argument(
        "--export-json",
        type=str,
        default=None,
        help="File path to save JSON benchmark results (e.g. logs/benchmark_results.json).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    print_banner()

    models = parse_comma_separated_list(args.models)
    variances = parse_comma_separated_list(args.variances)

    mode_str = "Offline Mock (Deterministic)" if args.mock else "Live API Inference (LiteLLM)"
    print(f"Execution Mode:       {mode_str}")
    print(f"Runs per Variance:    {args.runs}")
    print(f"Models to Evaluate:   {models or 'ALL Supported'}")
    print(f"Prompt Variances:     {variances or 'ALL (react, few_shot, direct_schema)'}")

    try:
        report = run_cost_benchmark(
            models=models,
            prompt_variances=variances,
            mock=args.mock,
            export_csv=args.export_csv,
            export_json=args.export_json,
            runs_per_variance=args.runs,
        )
    except Exception as exc:
        print(f"\n[ERROR] Benchmark execution failed: {exc}", file=sys.stderr)
        return 1

    print_model_table(report)
    print_variance_table(report)
    print_overall_summary(report)

    if args.export_csv:
        print(f"[EXPORT] CSV exported successfully to:  {args.export_csv}")
    if args.export_json:
        print(f"[EXPORT] JSON exported successfully to: {args.export_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
