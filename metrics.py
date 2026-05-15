"""
metrics.py  --  simple helpers for tracking run stats and experiment plots
"""

import time
import statistics
import os

# matplotlib is optional (only for plots)
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class MetricsTracker:
    """track metrics for a single CSP run"""

    def __init__(self, algorithm_name="Unknown"):
        self.algorithm_name = algorithm_name
        self.start_time = None
        self.end_time = None
        self.assignments = 0
        self.backtracks = 0
        self.constraint_checks = 0
        self.elapsed = 0.0
        self.success = False
        self.scheduled = 0
        self.total = 0

    def start(self):
        self.start_time = time.time()

    def finish(self, metrics_dict):
        """copy fields from metrics dict returned by algorithm"""
        self.end_time = time.time()
        self.elapsed = metrics_dict.get("time", 0.0)
        self.assignments = metrics_dict.get("assignments", 0)
        self.backtracks = metrics_dict.get("backtracks", 0)
        self.constraint_checks = metrics_dict.get("constraint_checks", 0)
        self.success = metrics_dict.get("valid", False)
        self.scheduled = metrics_dict.get("scheduled", 0)
        self.total = metrics_dict.get("total_courses", 0)

    def to_dict(self):
        return {
            "algorithm": self.algorithm_name,
            "success": self.success,
            "scheduled": self.scheduled,
            "total": self.total,
            "assignments": self.assignments,
            "backtracks": self.backtracks,
            "constraint_checks": self.constraint_checks,
            "time": self.elapsed,
        }

    def print_summary(self):
        sep = "=" * 55
        print(f"\n{sep}")
        print(f"  METRICS -- {self.algorithm_name}")
        print(sep)
        status = "SUCCESS" if self.success else "FAILED"
        print(f"  Status              : {status}")
        print(f"  Scheduled           : {self.scheduled}/{self.total}")
        print(f"  Variable Assignments: {self.assignments}")
        print(f"  Backtracks          : {self.backtracks}")
        print(f"  Constraint Checks   : {self.constraint_checks}")
        print(f"  Execution Time      : {self.elapsed:.4f} seconds")
        print(sep)


class ExperimentResult:
    """aggregate metrics for multiple runs of same config"""

    def __init__(self, label=""):
        self.label = label
        self.runs = []  # list of dicts

    def add_run(self, metrics_dict):
        self.runs.append(metrics_dict)

    def success_rate(self):
        if not self.runs:
            return 0.0
        count = 0
        for r in self.runs:
            if r["success"]:
                count += 1
        return count / float(len(self.runs))

    def _values_for_key(self, key):
        vals = []
        for r in self.runs:
            if r["success"]:
                vals.append(r[key])
        return vals

    def avg(self, key):
        vals = self._values_for_key(key)
        if not vals:
            return float("nan")
        return statistics.mean(vals)

    def std(self, key):
        vals = self._values_for_key(key)
        if len(vals) <= 1:
            return 0.0
        return statistics.stdev(vals)

    def summary(self):
        return {
            "label": self.label,
            "runs": len(self.runs),
            "success_rate": self.success_rate(),
            "avg_time": self.avg("time"),
            "std_time": self.std("time"),
            "avg_backtracks": self.avg("backtracks"),
            "avg_constraint_checks": self.avg("constraint_checks"),
            "avg_assignments": self.avg("assignments"),
        }

    def print_summary(self):
        s = self.summary()
        sep = "-" * 60
        print(f"\n  [{self.label}]")
        print(sep)
        print(f"  Runs          : {s['runs']}")
        print(f"  Success Rate  : {s['success_rate']*100:.1f}%")
        print(
            f"  Avg Time      : {s['avg_time']:.4f}s  "
            f"(± {s['std_time']:.4f}s)"
        )
        print(f"  Avg Backtracks: {s['avg_backtracks']:.1f}")
        print(f"  Avg CC        : {s['avg_constraint_checks']:.1f}")
        print(sep)


def print_experiment_table(results, title="Experiment Results"):
    """simple text table comparing many ExperimentResult objects"""
    sep = "=" * 75
    print(f"\n{sep}")
    print(f"  {title}")
    print(sep)

    header = (
        f"  {'Algorithm':<28} {'Succ%':>6} {'Avg Time':>10} "
        f"{'Avg BT':>9} {'Avg CC':>10}"
    )
    print(header)
    print("-" * 75)

    for res in results:
        s = res.summary()
        sr = f"{s['success_rate']*100:.0f}%"
        t = f"{s['avg_time']:.4f}s"
        bt = f"{s['avg_backtracks']:.0f}"
        cc = f"{s['avg_constraint_checks']:.0f}"
        print(f"  {s['label']:<28} {sr:>6} {t:>10} {bt:>9} {cc:>10}")

    print(sep)


def print_heuristic_comparison_table(results, title="Heuristic Impact"):
    """table for experiment 2 showing % reduction vs baseline"""
    sep = "=" * 80
    print(f"\n{sep}")
    print(f"  {title}")
    print(sep)

    if not results:
        print("  No results.")
        return

    baseline = results[0].summary()

    header = (
        f"  {'Configuration':<30} {'BT Reduc%':>10} "
        f"{'CC Reduc%':>10} {'Time Reduc%':>12} {'Succ%':>7}"
    )
    print(header)
    print("-" * 80)

    for res in results:
        s = res.summary()

        base_bt = baseline["avg_backtracks"]
        if not base_bt:
            base_bt = 1
        base_cc = baseline["avg_constraint_checks"]
        if not base_cc:
            base_cc = 1
        base_t = baseline["avg_time"]
        if not base_t:
            base_t = 1e-9

        bt_red = (1 - s["avg_backtracks"] / base_bt) * 100
        cc_red = (1 - s["avg_constraint_checks"] / base_cc) * 100
        t_red = (1 - s["avg_time"] / base_t) * 100
        sr = f"{s['success_rate']*100:.0f}%"

        print(
            f"  {s['label']:<30} {bt_red:>9.1f}% "
            f"{cc_red:>9.1f}% {t_red:>11.1f}% {sr:>7}"
        )

    print(sep)


def plot_algorithm_comparison(results, output_path="results/exp1_comparison.png"):
    """bar chart comparing algorithms on time / backtracks / success"""
    if not MATPLOTLIB_AVAILABLE:
        print("  [INFO] matplotlib not available -- skipping plot.")
        return

    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    labels = [r.label for r in results]
    times = [r.avg("time") for r in results]
    bts = [r.avg("backtracks") for r in results]
    success = [r.success_rate() * 100 for r in results]

    x = list(range(len(labels)))
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.suptitle("Algorithm Comparison", fontsize=14, fontweight="bold")

    axes[0].bar(x, times, color="steelblue")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=15, ha="right", fontsize=9)
    axes[0].set_title("Average Time (s)")
    axes[0].set_ylabel("seconds")

    axes[1].bar(x, bts, color="tomato")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=15, ha="right", fontsize=9)
    axes[1].set_title("Average Backtracks")
    axes[1].set_ylabel("count")

    axes[2].bar(x, success, color="seagreen")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(labels, rotation=15, ha="right", fontsize=9)
    axes[2].set_title("Success Rate (%)")
    axes[2].set_ylabel("%")
    axes[2].set_ylim(0, 110)

    plt.tight_layout()
    plt.savefig(output_path, dpi=120)
    plt.close()
    print(f"  [Plot saved] {output_path}")


def plot_phase_transition(
    tightness_vals,
    sat_rates,
    search_costs,
    output_path="results/exp3_phase_transition.png",
):
    """plot satisfiability rate and search cost vs tightness"""
    if not MATPLOTLIB_AVAILABLE:
        print("  [INFO] matplotlib not available -- skipping plot.")
        return

    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Phase Transition Analysis", fontsize=14, fontweight="bold")

    ax1.plot(tightness_vals, sat_rates, "bo-", linewidth=2, markersize=6)
    ax1.set_xlabel("Constraint Tightness")
    ax1.set_ylabel("Satisfiability Rate")
    ax1.set_title("Satisfiability vs Tightness")
    ax1.set_ylim(-0.05, 1.05)
    ax1.axhline(y=0.5, color="red", linestyle="--", alpha=0.5, label="50% threshold")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.plot(tightness_vals, search_costs, "r^-", linewidth=2, markersize=6)
    ax2.set_xlabel("Constraint Tightness")
    ax2.set_ylabel("Avg Backtracks")
    ax2.set_title("Search Cost vs Tightness")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=120)
    plt.close()
    print(f"  [Plot saved] {output_path}")


def plot_heuristic_impact(results, output_path="results/exp2_heuristics.png"):
    """bar chart for heuristic comparison results"""
    if not MATPLOTLIB_AVAILABLE:
        print("  [INFO] matplotlib not available -- skipping plot.")
        return

    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    labels = [r.label for r in results]
    bts = [r.avg("backtracks") for r in results]
    ccs = [r.avg("constraint_checks") for r in results]
    times = [r.avg("time") for r in results]

    x = list(range(len(labels)))
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.suptitle("Heuristic Impact", fontsize=14, fontweight="bold")

    axes[0].bar(x, bts, color="coral")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    axes[0].set_title("Avg Backtracks")

    axes[1].bar(x, ccs, color="cornflowerblue")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    axes[1].set_title("Avg Constraint Checks")

    axes[2].bar(x, times, color="mediumseagreen")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    axes[2].set_title("Avg Time (s)")

    plt.tight_layout()
    plt.savefig(output_path, dpi=120)
    plt.close()
    print(f"  [Plot saved] {output_path}")


def plot_systematic_vs_local(
    mac_result,
    mc_result,
    output_path="results/exp4_sys_vs_local.png",
):
    """compare MAC vs Min-Conflicts side-by-side"""
    if not MATPLOTLIB_AVAILABLE:
        print("  [INFO] matplotlib not available -- skipping plot.")
        return

    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    labels = ["MAC (Systematic)", "Min-Conflicts (Local)"]
    times = [mac_result.avg("time"), mc_result.avg("time")]
    success = [mac_result.success_rate() * 100, mc_result.success_rate() * 100]

    x = [0, 1]
    fig, axes = plt.subplots(1, 2, figsize=(9, 5))
    fig.suptitle("Systematic vs Local Search", fontsize=13, fontweight="bold")

    colors = ["steelblue", "darkorange"]

    axes[0].bar(x, times, color=colors)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, fontsize=9)
    axes[0].set_title("Average Time (s)")
    axes[0].set_ylabel("seconds")

    axes[1].bar(x, success, color=colors)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, fontsize=9)
    axes[1].set_title("Success Rate (%)")
    axes[1].set_ylabel("%")
    axes[1].set_ylim(0, 110)

    plt.tight_layout()
    plt.savefig(output_path, dpi=120)
    plt.close()
    print(f"  [Plot saved] {output_path}")