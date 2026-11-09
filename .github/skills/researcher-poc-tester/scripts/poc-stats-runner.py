#!/usr/bin/env python3
r"""
poc-stats-runner.py — Statistical benchmark harness for empirical Proof-of-Concept testing.

Executes commands or test scripts across multiple iterations with automated JIT/runtime warmup,
high-resolution timing, statistical percentiles (P50, P90, P95, P99), standard deviation,
and relative speedup calculations.

Usage:
    # Benchmark a single command:
    .\.venv\Scripts\python.exe .github/skills/researcher-poc-tester/scripts/poc-stats-runner.py run --cmd "node scratch/pocs/io-test.mjs" --iterations 30 --warmup 5

    # Compare two competing approaches:
    .\.venv\Scripts\python.exe .github/skills/researcher-poc-tester/scripts/poc-stats-runner.py compare \
        --baseline "python scratch/pocs/numpy_bench.py" --baseline-label "NumPy Vectorized" \
        --candidate "python scratch/pocs/polars_bench.py" --candidate-label "Polars Lazy Arrow" \
        --iterations 25 --warmup 5
"""

import argparse
import json
import math
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional


def calculate_percentile(sorted_data: List[float], percentile: float) -> float:
    """Calculate percentile using linear interpolation between nearest ranks."""
    if not sorted_data:
        return 0.0
    if len(sorted_data) == 1:
        return sorted_data[0]
    
    k = (len(sorted_data) - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[int(f)] * (c - k)
    d1 = sorted_data[int(c)] * (k - f)
    return d0 + d1


def compute_statistics(durations_ms: List[float], label: str = "Execution") -> Dict[str, Any]:
    """Compute comprehensive statistical metrics from a sample of durations in milliseconds."""
    if not durations_ms:
        return {
            "label": label,
            "samples": 0,
            "mean_ms": 0.0,
            "median_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "p90_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "stddev_ms": 0.0,
            "ops_per_sec": 0.0,
        }

    sorted_d = sorted(durations_ms)
    n = len(sorted_d)
    mean_val = sum(sorted_d) / n
    variance = sum((x - mean_val) ** 2 for x in sorted_d) / (n - 1) if n > 1 else 0.0
    stddev_val = math.sqrt(variance)
    median_val = calculate_percentile(sorted_d, 50.0)
    p90_val = calculate_percentile(sorted_d, 90.0)
    p95_val = calculate_percentile(sorted_d, 95.0)
    p99_val = calculate_percentile(sorted_d, 99.0)
    ops_sec = (1000.0 / mean_val) if mean_val > 0 else 0.0

    return {
        "label": label,
        "samples": n,
        "mean_ms": round(mean_val, 3),
        "median_ms": round(median_val, 3),
        "min_ms": round(sorted_d[0], 3),
        "max_ms": round(sorted_d[-1], 3),
        "p90_ms": round(p90_val, 3),
        "p95_ms": round(p95_val, 3),
        "p99_ms": round(p99_val, 3),
        "stddev_ms": round(stddev_val, 3),
        "ops_per_sec": round(ops_sec, 2),
    }


def execute_iteration(cmd: str, timeout_sec: int) -> float:
    """Execute a single iteration with high-resolution wall-clock timer."""
    start_ns = time.perf_counter_ns()
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout_sec)
    end_ns = time.perf_counter_ns()

    if proc.returncode != 0:
        err_msg = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"Command failed (exit code {proc.returncode}): {err_msg[:400]}")

    elapsed_ms = (end_ns - start_ns) / 1_000_000.0
    return elapsed_ms


def run_benchmark(cmd: str, iterations: int, warmup: int, timeout_sec: int, label: str) -> Dict[str, Any]:
    """Run warmup and recorded benchmark iterations."""
    print(f"[*] Benchmarking '{label}'...")
    print(f"    Command: {cmd}")
    print(f"    Warmup rounds: {warmup} | Recorded iterations: {iterations}")

    # Warmup phase (allows JIT compilation, disk cache warming, OS thread pool initialization)
    for w in range(warmup):
        try:
            execute_iteration(cmd, timeout_sec)
        except Exception as e:
            print(f"    [!] Warmup iteration {w + 1} failed: {e}", file=sys.stderr)
            raise

    # Recorded phase
    durations: List[float] = []
    for i in range(iterations):
        try:
            dur = execute_iteration(cmd, timeout_sec)
            durations.append(dur)
            sys.stdout.write(f"\r    Progress: [{i + 1}/{iterations}] last: {dur:.2f}ms")
            sys.stdout.flush()
        except Exception as e:
            print(f"\n    [!] Recorded iteration {i + 1} failed: {e}", file=sys.stderr)
            raise

    print()
    stats = compute_statistics(durations, label=label)
    return stats


def format_markdown_table(stats_list: List[Dict[str, Any]], baseline_label: Optional[str] = None) -> str:
    """Format benchmark statistics into a readable GitHub-flavored markdown table."""
    baseline_stats = None
    if baseline_label:
        for s in stats_list:
            if s["label"] == baseline_label:
                baseline_stats = s
                break

    lines = [
        "| Approach / Scenario | Samples | Median (P50) | P95 | P99 | Min | Max | StdDev (σ) | Throughput (ops/s) | Relative Speedup |",
        "|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for s in stats_list:
        speedup_str = "Baseline (1.00x)"
        if baseline_stats and baseline_stats["mean_ms"] > 0:
            if s["label"] != baseline_stats["label"]:
                ratio = baseline_stats["median_ms"] / s["median_ms"] if s["median_ms"] > 0 else 1.0
                if ratio >= 1.0:
                    speedup_str = f"**{ratio:.2f}x faster** 🚀"
                else:
                    slower = 1.0 / ratio if ratio > 0 else 0.0
                    speedup_str = f"{slower:.2f}x slower 🔻"

        lines.append(
            f"| **{s['label']}** | {s['samples']} | {s['median_ms']} ms | {s['p95_ms']} ms | {s['p99_ms']} ms | "
            f"{s['min_ms']} ms | {s['max_ms']} ms | ±{s['stddev_ms']} ms | {s['ops_per_sec']} | {speedup_str} |"
        )

    return "\n".join(lines)


def cmd_run(args: argparse.Namespace) -> None:
    stats = run_benchmark(
        cmd=args.cmd,
        iterations=args.iterations,
        warmup=args.warmup,
        timeout_sec=args.timeout,
        label=args.label or "Test Run",
    )

    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        print("\n" + "=" * 70)
        print("EMPIRICAL BENCHMARK RESULTS")
        print("=" * 70)
        print(format_markdown_table([stats]))
        print("=" * 70)


def cmd_compare(args: argparse.Namespace) -> None:
    baseline_stats = run_benchmark(
        cmd=args.baseline,
        iterations=args.iterations,
        warmup=args.warmup,
        timeout_sec=args.timeout,
        label=args.baseline_label,
    )

    candidate_stats = run_benchmark(
        cmd=args.candidate,
        iterations=args.iterations,
        warmup=args.warmup,
        timeout_sec=args.timeout,
        label=args.candidate_label,
    )

    all_stats = [baseline_stats, candidate_stats]

    if args.json:
        print(json.dumps(all_stats, indent=2))
    else:
        print("\n" + "=" * 80)
        print("EMPIRICAL COMPARATIVE BENCHMARK REPORT")
        print("=" * 80)
        table = format_markdown_table(all_stats, baseline_label=args.baseline_label)
        print(table)
        print("=" * 80)

        diff_p50 = candidate_stats["median_ms"] - baseline_stats["median_ms"]
        ratio = baseline_stats["median_ms"] / candidate_stats["median_ms"] if candidate_stats["median_ms"] > 0 else 1.0
        
        print("\n### Executive Takeaway")
        if ratio > 1.05:
            print(f"- **Outcome:** `{args.candidate_label}` outperformed `{args.baseline_label}` by **{ratio:.2f}x** (median reduction of {abs(diff_p50):.2f} ms).")
        elif ratio < 0.95:
            slower = 1.0 / ratio if ratio > 0 else 0.0
            print(f"- **Outcome:** `{args.candidate_label}` is **{slower:.2f}x slower** than `{args.baseline_label}` (median increase of {abs(diff_p50):.2f} ms).")
        else:
            print(f"- **Outcome:** No statistically significant performance difference observed between `{args.baseline_label}` and `{args.candidate_label}` (variance within ±5%).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Empirical PoC Benchmark & Statistics Runner")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # run command
    p_run = subparsers.add_parser("run", help="Benchmark a single approach")
    p_run.add_argument("--cmd", required=True, help="Shell command or script execution line")
    p_run.add_argument("--label", default="Benchmark", help="Label for this benchmark")
    p_run.add_argument("--iterations", type=int, default=20, help="Number of recorded iterations (default: 20)")
    p_run.add_argument("--warmup", type=int, default=5, help="Number of warmup iterations (default: 5)")
    p_run.add_argument("--timeout", type=int, default=120, help="Per-iteration timeout in seconds (default: 120)")
    p_run.add_argument("--json", action="store_true", help="Output results in JSON format")

    # compare command
    p_comp = subparsers.add_parser("compare", help="Compare two competing approaches")
    p_comp.add_argument("--baseline", required=True, help="Baseline command (Approach A)")
    p_comp.add_argument("--baseline-label", default="Approach A (Baseline)", help="Label for baseline")
    p_comp.add_argument("--candidate", required=True, help="Candidate command (Approach B)")
    p_comp.add_argument("--candidate-label", default="Approach B (Candidate)", help="Label for candidate")
    p_comp.add_argument("--iterations", type=int, default=20, help="Number of recorded iterations (default: 20)")
    p_comp.add_argument("--warmup", type=int, default=5, help="Number of warmup iterations (default: 5)")
    p_comp.add_argument("--timeout", type=int, default=120, help="Per-iteration timeout in seconds (default: 120)")
    p_comp.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    if args.subcommand == "run":
        cmd_run(args)
    elif args.subcommand == "compare":
        cmd_compare(args)


if __name__ == "__main__":
    main()
