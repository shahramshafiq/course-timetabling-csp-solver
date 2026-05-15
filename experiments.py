"""
experiments.py  --  runs the 4 experiments for the CSP timetabling project
"""

import os
import random
import copy

from timetable import build_timetabling_csp
from algorithms import solve
from heuristics import get_var_heuristic, get_val_heuristic
from metrics import (
    ExperimentResult,
    print_experiment_table,
    print_heuristic_comparison_table,
    plot_algorithm_comparison,
    plot_heuristic_impact,
    plot_phase_transition,
    plot_systematic_vs_local,
)
from generator import (
    InstanceGenerator,
    generate_instances,
    EXPERIMENT_1_CONFIGS,
    get_phase_transition_configs,
)


RESULTS_DIR = "results"
NUM_RUNS = 5  # runs per configuration


# small helper to build and solve one instance from a folder
def _run_once(input_dir, algorithm, var_h_name="none",
              val_h_name="none", seed=None):
    csp, courses, rooms, timeslots, students, avail, meta = build_timetabling_csp(
        input_dir
    )

    var_h = get_var_heuristic(var_h_name)
    val_h = get_val_heuristic(val_h_name)

    solution, metrics = solve(
        csp,
        algorithm=algorithm,
        var_heuristic=var_h,
        val_heuristic=val_h,
        mc_steps=5000,
        seed=seed,
    )

    metrics["total_courses"] = meta["num_courses"]
    if solution:
        metrics["scheduled"] = len(solution)
    else:
        metrics["scheduled"] = 0
    return metrics


# helper that generates a fresh instance then solves it
def _generate_and_run(cfg, algorithm, var_h="none",
                      val_h="none", run_id=0):
    seed = cfg.get("seed", 0) + run_id * 7
    tmp_dir = os.path.join("instances", "tmp_exp", f"run{run_id}_{algorithm}")
    os.makedirs(tmp_dir, exist_ok=True)

    if "rooms" in cfg:
        num_rooms = cfg["rooms"]
    else:
        num_rooms = int(cfg["courses"] * 0.7)

    num_slots = cfg.get("slots", 20)
    density = cfg.get("density", 0.3)
    tightness = cfg.get("tightness", 0.3)

    gen = InstanceGenerator(
        num_courses=cfg["courses"],
        num_rooms=num_rooms,
        num_slots=num_slots,
        density=density,
        tightness=tightness,
        seed=seed,
    )
    gen.generate(tmp_dir)

    metrics = _run_once(tmp_dir, algorithm, var_h, val_h, seed=seed)
    return metrics


# Experiment 1: Algorithm Comparison
def experiment_1(num_runs=NUM_RUNS):
    sep = "=" * 65
    print("\n" + sep)
    print("  EXPERIMENT 1: Algorithm Comparison")
    print(sep)

    algorithms = [
        ("backtrack", "Backtracking"),
        ("fc", "Forward Checking"),
        ("mac", "MAC (AC-3)"),
        ("min_conflicts", "Min-Conflicts"),
    ]

    os.makedirs(RESULTS_DIR, exist_ok=True)
    all_results = []

    for cfg in EXPERIMENT_1_CONFIGS:
        rooms_label = cfg.get("rooms", "auto")
        slots_label = cfg.get("slots", 20)
        size_label = (
            f"C{cfg['courses']}_R{rooms_label}"
            f"_S{slots_label}"
            f"_d{cfg['density']}_t{cfg['tightness']}"
        )
        print(f"\n  --- Config: {size_label} ---")

        for algo_key, algo_name in algorithms:
            label = f"{algo_name} | {size_label}"
            result = ExperimentResult(label=label)

            run = 0
            while run < num_runs:
                if algo_key != "min_conflicts":
                    metrics = _generate_and_run(
                        cfg, algo_key,
                        var_h="mrv_degree",
                        val_h="lcv",
                        run_id=run,
                    )
                else:
                    metrics = _generate_and_run(
                        cfg, algo_key, run_id=run
                    )
                result.add_run(metrics)
                run += 1

            result.print_summary()
            all_results.append(result)

    print_experiment_table(all_results, title="Experiment 1 -- Full Results")

    out_path = os.path.join(RESULTS_DIR, "exp1_comparison.png")
    plot_algorithm_comparison(all_results, output_path=out_path)

    print("\n  [Experiment 1 Complete]")
    return all_results


# Experiment 2: Heuristic Impact
def experiment_2(num_runs=NUM_RUNS):
    sep = "=" * 65
    print("\n" + sep)
    print("  EXPERIMENT 2: Heuristic Impact")
    print(sep)

    cfg = {
        "courses": 20,
        "rooms": 16,
        "slots": 30,
        "density": 0.5,
        "tightness": 0.5,
    }

    heuristic_configs = [
        ("none", "none", "No Heuristics"),
        ("mrv", "none", "MRV Only"),
        ("mrv_degree", "none", "MRV + Degree"),
        ("mrv_degree", "lcv", "MRV + Degree + LCV"),
    ]

    os.makedirs(RESULTS_DIR, exist_ok=True)
    all_results = []

    for var_h, val_h, label in heuristic_configs:
        result = ExperimentResult(label=label)
        print(f"\n  Testing: {label}")

        run = 0
        while run < num_runs:
            metrics = _generate_and_run(
                cfg,
                "mac",
                var_h=var_h,
                val_h=val_h,
                run_id=run,
            )
            result.add_run(metrics)
            run += 1

        result.print_summary()
        all_results.append(result)

    print_heuristic_comparison_table(
        all_results, title="Experiment 2 -- Heuristic Impact"
    )

    out_path = os.path.join(RESULTS_DIR, "exp2_heuristics.png")
    plot_heuristic_impact(all_results, output_path=out_path)

    print("\n  [Experiment 2 Complete]")
    return all_results


# Experiment 3: Phase Transition
def experiment_3(num_runs=3):
    sep = "=" * 65
    print("\n" + sep)
    print("  EXPERIMENT 3: Phase Transition Analysis")
    print(sep)

    tightness_vals = []
    i = 1
    while i < 10:
        tight = round(i * 0.1, 1)
        tightness_vals.append(tight)
        i += 1

    configs = get_phase_transition_configs(tightness_vals)

    os.makedirs(RESULTS_DIR, exist_ok=True)

    sat_rates = []
    search_costs = []

    for cfg in configs:
        t = cfg["tightness"]
        successes = 0
        total_bt = 0

        run = 0
        while run < num_runs:
            metrics = _generate_and_run(
                cfg,
                "mac",
                var_h="mrv_degree",
                val_h="lcv",
                run_id=run,
            )
            if metrics.get("valid", False):
                successes += 1
            total_bt += metrics.get("backtracks", 0)
            run += 1

        sat_rate = successes / num_runs
        avg_bt = total_bt / num_runs
        sat_rates.append(sat_rate)
        search_costs.append(avg_bt)

        if sat_rate > 0.5:
            status = "SAT"
        else:
            status = "UNSAT"

        print(
            f"  Tightness={t:.1f}  |  Sat Rate={sat_rate:.2f}"
            f"  |  Avg BT={avg_bt:.1f}  [{status}]"
        )

    out_path = os.path.join(RESULTS_DIR, "exp3_phase_transition.png")
    plot_phase_transition(
        tightness_vals, sat_rates, search_costs, output_path=out_path
    )

    idx = 0
    while idx < len(sat_rates):
        sr = sat_rates[idx]
        if sr < 0.5:
            print(
                f"\n  Phase transition occurs around "
                f"tightness = {tightness_vals[idx]:.1f}"
            )
            break
        idx += 1

    print("\n  [Experiment 3 Complete]")
    return tightness_vals, sat_rates, search_costs


# Experiment 4: Systematic vs Local Search
def experiment_4(num_runs=NUM_RUNS):
    sep = "=" * 65
    print("\n" + sep)
    print("  EXPERIMENT 4: Systematic vs Local Search")
    print(sep)

    configs = [
        {
            "courses": 10,
            "rooms": 8,
            "slots": 20,
            "density": 0.3,
            "tightness": 0.3,
            "label": "Easy (10 courses)",
        },
        {
            "courses": 20,
            "rooms": 16,
            "slots": 30,
            "density": 0.5,
            "tightness": 0.5,
            "label": "Medium (20 courses)",
        },
        {
            "courses": 30,
            "rooms": 24,
            "slots": 40,
            "density": 0.5,
            "tightness": 0.7,
            "label": "Hard (30 courses)",
        },
    ]

    os.makedirs(RESULTS_DIR, exist_ok=True)

    mac_total = ExperimentResult(label="MAC (all configs)")
    mc_total = ExperimentResult(label="Min-Conflicts (all configs)")

    for cfg in configs:
        label = cfg.get("label", "Unknown")
        print(f"\n  --- {label} ---")

        mac_result = ExperimentResult(label=f"MAC | {label}")
        mc_result = ExperimentResult(label=f"Min-Conflicts | {label}")

        run = 0
        while run < num_runs:
            m1 = _generate_and_run(
                cfg,
                "mac",
                var_h="mrv_degree",
                val_h="lcv",
                run_id=run,
            )
            m2 = _generate_and_run(
                cfg,
                "min_conflicts",
                run_id=run,
            )

            mac_result.add_run(m1)
            mc_result.add_run(m2)
            mac_total.add_run(m1)
            mc_total.add_run(m2)
            run += 1

        mac_result.print_summary()
        mc_result.print_summary()

        mac_sr = mac_result.success_rate() * 100
        mc_sr = mc_result.success_rate() * 100
        mac_t = mac_result.avg("time")
        mc_t = mc_result.avg("time")

        print(f"\n  Analysis for {label}:")
        if mac_sr > mc_sr:
            print(
                f"    MAC is more reliable "
                f"({mac_sr:.0f}% vs {mc_sr:.0f}% success)"
            )
        elif mc_sr > mac_sr:
            print(
                f"    Min-Conflicts is more reliable "
                f"({mc_sr:.0f}% vs {mac_sr:.0f}% success)"
            )
        else:
            print(f"    Both equally reliable ({mac_sr:.0f}% success)")

        if mac_t < mc_t:
            print(f"    MAC is faster ({mac_t:.4f}s vs {mc_t:.4f}s)")
        else:
            print(f"    Min-Conflicts is faster ({mc_t:.4f}s vs {mac_t:.4f}s)")

    print_experiment_table(
        [mac_total, mc_total],
        title="Experiment 4 -- Overall Systematic vs Local",
    )

    out_path = os.path.join(RESULTS_DIR, "exp4_sys_vs_local.png")
    plot_systematic_vs_local(mac_total, mc_total, output_path=out_path)

    print("\n  Key Insights:")
    print("    - MAC guarantees completeness (finds solution if one exists)")
    print("    - Min-Conflicts is faster on large loosely-constrained instances")
    print("    - Min-Conflicts can get stuck in local optima (no backtracking)")
    print("    - MAC + MRV+Degree+LCV is strong on tightly constrained problems")

    print("\n  [Experiment 4 Complete]")
    return mac_total, mc_total


# run all experiments in order
def run_all():
    print("\n" + "=" * 65)
    print("  RUNNING ALL EXPERIMENTS")
    print("  AI2002 -- Assignment 02 -- Question 1")
    print("=" * 65)

    print("\n  Generating experiment instances...")
    os.makedirs("instances/exp", exist_ok=True)

    experiment_1()
    experiment_2()
    experiment_3()
    experiment_4()

    print("\n" + "=" * 65)
    print("  ALL EXPERIMENTS COMPLETE")
    print(f"  Results and plots saved to: {RESULTS_DIR}/")
    print("=" * 65)


if __name__ == "__main__":
    run_all()