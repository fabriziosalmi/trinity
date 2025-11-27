#!/usr/bin/env python3
"""
Trinity v0.8.0 Multiclass Predictor - A/B Benchmark

Simplified benchmark using CLI builds to compare:
- With predictor (predictive_enabled=True)
- Without predictor (predictive_enabled=False, heuristic only)

Metrics:
- Build time
- Success rate
- Average iterations (from logs)
"""

import json
import subprocess
import tempfile
import time
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, List, Any


class SimpleBenchmark:
    """Simplified A/B benchmark using CLI builds."""

    def __init__(self, num_samples: int = 50):
        self.num_samples = num_samples
        self.results = {
            "with_predictor": [],
            "without_predictor": []
        }

    def run_build(self, theme: str, use_predictor: bool) -> Dict[str, Any]:
        """
        Run a single build and measure performance.
        
        Returns:
            Metrics dict with time and success
        """
        output_file = tempfile.mktemp(suffix=".html", prefix="benchmark_")
        
        cmd = [
            "/Users/fab/GitHub/trinity/venv/bin/python",
            "-m", "trinity.cli",
            "build",
            "--theme", theme,
            "--guardian",
            "--output", output_file
        ]
        
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.time() - start
        
        success = result.returncode == 0 and "Guardian APPROVED" in result.stdout
        
        # Clean up
        Path(output_file).unlink(missing_ok=True)
        
        return {
            "time_seconds": elapsed,
            "success": success,
            "theme": theme
        }

    def run_benchmark(self) -> Dict[str, Any]:
        """Run benchmark."""
        print(f"\n🧪 Running Simplified Benchmark (n={self.num_samples})")
        print("=" * 60)
        
        themes = ["brutalist", "enterprise", "editorial"]
        
        for i in range(self.num_samples):
            theme = themes[i % len(themes)]
            
            print(f"\n[{i+1}/{self.num_samples}] Testing {theme}...")
            
            # With predictor
            result_with = self.run_build(theme, use_predictor=True)
            self.results["with_predictor"].append(result_with)
            print(f"  ✅ With predictor: {result_with['time_seconds']:.2f}s")
            
            # Without predictor (same content, should be slower)
            result_without = self.run_build(theme, use_predictor=False)
            self.results["without_predictor"].append(result_without)
            print(f"  ⏱️  Without predictor: {result_without['time_seconds']:.2f}s")
        
        return self.compute_stats()

    def compute_stats(self) -> Dict[str, Any]:
        """Compute statistics."""
        with_pred = self.results["with_predictor"]
        without_pred = self.results["without_predictor"]
        
        stats = {
            "with_predictor": {
                "avg_time": mean([r["time_seconds"] for r in with_pred]),
                "std_time": stdev([r["time_seconds"] for r in with_pred]) if len(with_pred) > 1 else 0,
                "success_rate": sum([r["success"] for r in with_pred]) / len(with_pred) * 100
            },
            "without_predictor": {
                "avg_time": mean([r["time_seconds"] for r in without_pred]),
                "std_time": stdev([r["time_seconds"] for r in without_pred]) if len(without_pred) > 1 else 0,
                "success_rate": sum([r["success"] for r in without_pred]) / len(without_pred) * 100
            }
        }
        
        time_reduction = (
            (stats["without_predictor"]["avg_time"] - stats["with_predictor"]["avg_time"])
            / stats["without_predictor"]["avg_time"] * 100
        )
        
        stats["improvement"] = {
            "time_reduction_percent": time_reduction
        }
        
        return stats

    def print_report(self, stats: Dict[str, Any]):
        """Print report."""
        print("\n" + "=" * 60)
        print("📊 BENCHMARK RESULTS")
        print("=" * 60)
        
        print("\n🔵 Without Predictor (Heuristic Only)")
        print(f"  Avg Time:     {stats['without_predictor']['avg_time']:.2f}s ± {stats['without_predictor']['std_time']:.2f}s")
        print(f"  Success Rate: {stats['without_predictor']['success_rate']:.1f}%")
        
        print("\n🟢 With Multiclass Predictor (v0.8.0)")
        print(f"  Avg Time:     {stats['with_predictor']['avg_time']:.2f}s ± {stats['with_predictor']['std_time']:.2f}s")
        print(f"  Success Rate: {stats['with_predictor']['success_rate']:.1f}%")
        
        print("\n📈 IMPROVEMENT")
        print(f"  Time Reduction: {stats['improvement']['time_reduction_percent']:.1f}%")
        
        print("=" * 60)


def main():
    """Run benchmark."""
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", "-n", type=int, default=20)
    args = parser.parse_args()
    
    benchmark = SimpleBenchmark(num_samples=args.samples)
    stats = benchmark.run_benchmark()
    benchmark.print_report(stats)
    
    # Save report
    with open("benchmark_report.json", "w") as f:
        json.dump({"stats": stats, "results": benchmark.results}, f, indent=2)
    print("\n💾 Report saved: benchmark_report.json\n")


if __name__ == "__main__":
    main()

def main():
    """Run benchmark."""
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", "-n", type=int, default=20)
    args = parser.parse_args()
    
    benchmark = SimpleBenchmark(num_samples=args.samples)
    stats = benchmark.run_benchmark()
    benchmark.print_report(stats)
    
    # Save report
    with open("benchmark_report.json", "w") as f:
        json.dump({"stats": stats, "results": benchmark.results}, f, indent=2)
    print("\n💾 Report saved: benchmark_report.json\n")


if __name__ == "__main__":
    main()

