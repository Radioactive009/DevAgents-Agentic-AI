#!/usr/bin/env python3
"""
CLI Comparative Evaluation Runner for Agentic Design Patterns (Requirement 4).

Compares:
1. Blackboard + Evaluator-Optimizer (Thread-safe memory, O(1) isolated context, atomic rollback)
2. ReAct (Reasoning + Acting, O(N) context bloat, uncoordinated state)
3. Hierarchical Delegation (Top-down supervisor planning, scoped worker contexts)

Outputs formatted ASCII comparison tables, error recovery statistics,
and comprehensive architectural trade-off matrices. Supports structured exports
to CSV and JSON formats.

Usage:
    # Quick mock evaluation (default 5 runs)
    python compare_agentic_patterns.py

    # 10 runs with CSV and JSON exports
    python compare_agentic_patterns.py --runs 10 --export-json logs/pattern_benchmark.json --export-csv logs/pattern_benchmark.csv

    # Evaluate with specific pricing model
    python compare_agentic_patterns.py --model groq/llama-3.3-70b-versatile
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from src.evaluation.pattern_benchmark import (
    DEFAULT_BENCHMARK_MODEL,
    PatternBenchmarkMetrics,
    PatternComparisonResult,
    PatternTradeoffReport,
    evaluate_agentic_patterns,
    export_pattern_benchmark_to_csv,
    export_pattern_benchmark_to_json,
    generate_pattern_tradeoff_report,
)
from src.evaluation.pricing import get_supported_models, normalize_model_name


def print_banner() -> None:
    """Prints the pattern comparative evaluation banner."""
    print("=" * 100)
    print("   DEVAGENTS-AGI: AGENTIC DESIGN PATTERNS FORMAL COMPARATIVE EVALUATION (REQ 4)")
    print("   Empirical Comparison: Blackboard + Evaluator-Optimizer vs ReAct vs Hierarchical")
    print("=" * 100)


def print_comparison_table(result: PatternComparisonResult) -> None:
    """Prints formatted ASCII table of core evaluation metrics."""
    print("\n" + "=" * 100)
    print("   1. CORE COMPARATIVE PERFORMANCE & COST METRICS")
    print("=" * 100)

    header = (
        f"{'Pattern':<34} | {'Mean Lat':>8} | {'P95 (s)':>7} | {'Avg Prompt':>10} | "
        f"{'Avg Compl':>9} | {'Total ($)':>11} | {'Recovery':>8} | {'MTTR':>5} | {'Bloat':>6} | {'Race Res':>8}"
    )
    print(header)
    print("-" * len(header))

    for name, m in result.patterns.items():
        mean_lat = f"{m.mean_latency_s:.3f}s"
        p95_lat = f"{m.p95_latency_s:.3f}s"
        avg_prompt = f"{m.avg_prompt_tokens:.0f}"
        avg_compl = f"{m.avg_completion_tokens:.0f}"
        total_cost = f"${m.total_cost_usd:.6f}"
        rec_pct = f"{m.recovery_rate_pct:.1f}%"
        mttr = f"{m.mean_recovery_attempts:.2f}"
        bloat = f"{m.context_token_bloat_factor:.2f}x"
        race_res = f"{m.race_resistance_rate:.1f}%"

        print(
            f"{name:<34} | {mean_lat:>8} | {p95_lat:>7} | {avg_prompt:>10} | "
            f"{avg_compl:>9} | {total_cost:>11} | {rec_pct:>8} | {mttr:>5} | {bloat:>6} | {race_res:>8}"
        )
    print("-" * len(header))


def print_recovery_breakdown_table(result: PatternComparisonResult) -> None:
    """Prints error recovery and MTTR breakdown table."""
    print("\n" + "=" * 100)
    print("   2. ERROR RECOVERY & MEAN TIME TO REPAIR (MTTR) BREAKDOWN")
    print("=" * 100)

    header = (
        f"{'Pattern':<34} | {'Recovery Rate':>13} | {'Mean Attempts':>13} | "
        f"{'MTTR Duration':>13} | {'Atomic Rollback':>15} | {'Concurrency Safe':>16}"
    )
    print(header)
    print("-" * len(header))

    for name, m in result.patterns.items():
        rec_rate = f"{m.recovery_rate_pct:.1f}% (<=3 att)"
        mttr_att = f"{m.mean_recovery_attempts:.2f} att"
        mttr_dur = f"{m.mttr_seconds:.3f}s"
        atomic = "Yes (.bak)" if "Blackboard" in name else "No"
        safe = "YES (RLock)" if m.concurrency_safe and "Blackboard" in name else ("YES (Scoped)" if m.concurrency_safe else "NO (Race Prone)")

        print(
            f"{name:<34} | {rec_rate:>13} | {mttr_att:>13} | "
            f"{mttr_dur:>13} | {atomic:>15} | {safe:>16}"
        )
    print("-" * len(header))


def print_tradeoff_matrix(report: PatternTradeoffReport) -> None:
    """Prints comprehensive architectural trade-off matrix."""
    print("\n" + "=" * 100)
    print("   3. COMPREHENSIVE PATTERN TRADE-OFF MATRIX")
    print("=" * 100)

    for pattern_name, matrix in report.tradeoff_matrix.items():
        print(f"\n[+] PATTERN: {pattern_name.upper()}")
        print(f"    - Architecture Complexity:  {matrix.get('architecture_complexity')}")
        print(f"    - Context Token Scaling:    {matrix.get('context_token_scaling')} (Bloat: {matrix.get('context_bloat_factor')}x)")
        print(f"    - Fault Tolerance Boundary: {matrix.get('fault_tolerance')}")
        print(f"    - Concurrency Safety:       {matrix.get('concurrency_safety')}")
        print(f"    - Error Recovery Rate:      {matrix.get('error_recovery_rate_pct')}% (MTTR: {matrix.get('mean_recovery_attempts')} attempts)")
        print(f"    - State Safety Score:       {matrix.get('state_safety_score')}/10.0")
        print(f"    - Best-Fit Use Cases:       {matrix.get('best_fit_use_cases')}")


def print_recommendations(report: PatternTradeoffReport) -> None:
    """Prints architectural deployment recommendations."""
    print("\n" + "=" * 100)
    print("   4. ARCHITECTURAL DEPLOYMENT RECOMMENDATIONS")
    print("=" * 100)
    for rec in report.recommendations:
        print(f"\n  * {rec}")
    print("\n" + "=" * 100)


def build_parser() -> argparse.ArgumentParser:
    """Constructs the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Formal comparative evaluation harness for agentic design patterns.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of evaluation repetitions per pattern (default: 5).",
    )
    parser.add_argument(
        "--mock",
        dest="mock",
        action="store_true",
        default=True,
        help="Execute deterministic authentic simulation benchmark (default: True).",
    )
    parser.add_argument(
        "--live",
        dest="mock",
        action="store_false",
        help="Execute live LLM queries via LiteLLM.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_BENCHMARK_MODEL,
        help=(
            f"Pricing model identifier (default: {DEFAULT_BENCHMARK_MODEL}). "
            f"Supported models: {', '.join(get_supported_models())}"
        ),
    )
    parser.add_argument(
        "--export-json",
        type=str,
        default=None,
        help="File path to save JSON benchmark evaluation report (e.g. logs/pattern_benchmark.json).",
    )
    parser.add_argument(
        "--export-csv",
        type=str,
        default=None,
        help="File path to save CSV benchmark evaluation report (e.g. logs/pattern_benchmark.csv).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    print_banner()

    try:
        canonical_model = normalize_model_name(args.model)
    except ValueError as exc:
        print(f"\n[ERROR] Invalid model: {exc}", file=sys.stderr)
        return 1

    mode_str = "Authentic Simulation (Deterministic)" if args.mock else "Live Model Execution (LiteLLM)"
    print(f"Execution Mode:       {mode_str}")
    print(f"Repetitions / Pattern:{args.runs}")
    print(f"Pricing Model:        {canonical_model}")
    print(f"Patterns Evaluated:   Blackboard + Evaluator-Optimizer, ReAct, Hierarchical")

    try:
        result = evaluate_agentic_patterns(
            runs=args.runs,
            mock=args.mock,
            model=canonical_model,
        )
        report = generate_pattern_tradeoff_report(result=result)
    except Exception as exc:
        print(f"\n[ERROR] Benchmark execution failed: {exc}", file=sys.stderr)
        return 1

    print_comparison_table(result)
    print_recovery_breakdown_table(result)
    print_tradeoff_matrix(report)
    print_recommendations(report)

    if args.export_json:
        export_pattern_benchmark_to_json(result, args.export_json)
        print(f"\n[EXPORT] JSON results exported successfully to: {args.export_json}")

    if args.export_csv:
        export_pattern_benchmark_to_csv(result, args.export_csv)
        print(f"[EXPORT] CSV results exported successfully to:  {args.export_csv}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
