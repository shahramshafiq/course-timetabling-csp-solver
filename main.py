"""
main.py  --  simple command line interface for the CSP timetabling solver
"""

import argparse
import os
import sys

from timetable import (
    build_timetabling_csp,
    print_solution,
    compute_soft_score,
)
from algorithms import solve
from heuristics import get_var_heuristic, get_val_heuristic
from metrics import MetricsTracker
from generator import InstanceGenerator
from experiments import (
    experiment_1,
    experiment_2,
    experiment_3,
    experiment_4,
    run_all,
)


def build_parser():
    """set up command line arguments"""
    parser = argparse.ArgumentParser(
        description="AI2002 -- CSP Timetabling Solver",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # solve mode
    parser.add_argument(
        "--input-dir",
        type=str,
        default=None,
        help="Directory with CSV files (courses, rooms, timeslots, etc.)",
    )
    parser.add_argument(
        "--algorithm",
        type=str,
        default="mac",
        choices=[
            "backtrack",
            "bt",
            "fc",
            "forward_checking",
            "mac",
            "ac3",
            "min_conflicts",
            "mc",
        ],
        help="Search algorithm (default: mac)",
    )
    parser.add_argument(
        "--var-heuristic",
        type=str,
        default="mrv_degree",
        choices=["none", "mrv", "degree", "mrv_degree", "random"],
        help="Variable ordering heuristic (default: mrv_degree)",
    )
    parser.add_argument(
        "--val-heuristic",
        type=str,
        default="lcv",
        choices=["none", "lcv", "random"],
        help="Value ordering heuristic (default: lcv)",
    )
    parser.add_argument(
        "--mc-steps",
        type=int,
        default=10000,
        help="Max steps for Min-Conflicts",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )

    # generate mode
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate a new CSP instance instead of solving",
    )
    parser.add_argument(
        "--courses",
        type=int,
        default=10,
        help="Number of course sections to generate",
    )
    parser.add_argument(
        "--rooms",
        type=int,
        default=None,
        help="Number of rooms (default: 70% of courses)",
    )
    parser.add_argument(
        "--slots",
        type=int,
        default=20,
        help="Number of time slots",
    )
    parser.add_argument(
        "--density",
        type=float,
        default=0.3,
        help="Constraint density 0.0-1.0",
    )
    parser.add_argument(
        "--tightness",
        type=float,
        default=0.3,
        help="Constraint tightness 0.0-1.0",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="instances/generated",
        help="Output directory for generated CSVs",
    )

    # experiment mode
    parser.add_argument(
        "--experiment",
        type=str,
        default=None,
        choices=["1", "2", "3", "4", "all"],
        help="Run a specific experiment (1-4) or all",
    )

    return parser


def run_solve(args):
    """load instance, solve it, and print results"""
    input_dir = args.input_dir

    if not os.path.isdir(input_dir):
        print(f"[ERROR] Directory not found: '{input_dir}'")
        sys.exit(1)

    print(f"\n  Loading instance from: {input_dir}")
    print(f"  Algorithm            : {args.algorithm.upper()}")
    print(f"  Variable Heuristic   : {args.var_heuristic}")
    print(f"  Value Heuristic      : {args.val_heuristic}")

    try:
        (
            csp,
            courses,
            rooms,
            timeslots,
            students,
            avail,
            meta,
        ) = build_timetabling_csp(input_dir)
    except FileNotFoundError as e:
        print(f"[ERROR] Missing CSV file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to load instance: {e}")
        sys.exit(1)

    print(f"\n  Courses   : {meta['num_courses']}")
    print(f"  Rooms     : {meta['num_rooms']}")
    print(f"  Slots     : {meta['num_slots']}")
    print(f"  Students  : {meta['num_students']}")
    print(f"  Pruned    : {meta['pruned_values']} domain values removed")
    print(f"  Constraints registered: {meta['constraint_pairs']} pairs")

    empty = []
    for v in csp.variables:
        if len(csp.domains[v]) == 0:
            empty.append(v)

    if empty:
        print("\n  [WARNING] These courses have empty domains after pruning:")
        for e in empty:
            print(f"    - {e}  ({courses[e]['name']})")
        print("  Consider adjusting rooms or timeslots to widen domains.")

    try:
        var_h = get_var_heuristic(args.var_heuristic)
        val_h = get_val_heuristic(args.val_heuristic)
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print("\n  Solving...")
    solution, metrics = solve(
        csp,
        algorithm=args.algorithm,
        var_heuristic=var_h,
        val_heuristic=val_h,
        mc_steps=args.mc_steps,
        seed=args.seed,
    )

    metrics["total_courses"] = meta["num_courses"]
    if solution:
        metrics["scheduled"] = len(solution)
    else:
        metrics["scheduled"] = 0
    metrics["valid"] = solution is not None

    algo_map = {
        "backtrack": "Backtracking",
        "bt": "Backtracking",
        "fc": "Forward Checking",
        "forward_checking": "Forward Checking",
        "mac": "MAC (AC-3)",
        "ac3": "MAC (AC-3)",
        "min_conflicts": "Min-Conflicts Local Search",
        "mc": "Min-Conflicts Local Search",
    }
    algo_name = algo_map.get(args.algorithm.lower(), args.algorithm)
    heur_parts = []
    if args.var_heuristic != "none":
        heur_parts.append(args.var_heuristic.upper())
    if args.val_heuristic != "none":
        heur_parts.append(args.val_heuristic.upper())
    if len(heur_parts) > 0:
        algo_name = algo_name + " + " + " + ".join(heur_parts)

    if solution:
        soft = compute_soft_score(solution, courses, avail)
    else:
        soft = 0

    print_solution(
        solution,
        courses,
        rooms,
        timeslots,
        algo_name,
        metrics,
        soft_score=soft,
    )


def run_generate(args):
    """generate one new random instance"""
    num_rooms = args.rooms
    if num_rooms is None:
        num_rooms = int(args.courses * 0.7)
        if num_rooms < 1:
            num_rooms = 1

    print("\n  Generating instance:")
    print(f"    Courses   : {args.courses}")
    print(f"    Rooms     : {num_rooms}")
    print(f"    Slots     : {args.slots}")
    print(f"    Density   : {args.density}")
    print(f"    Tightness : {args.tightness}")
    print(f"    Output    : {args.output_dir}")

    gen = InstanceGenerator(
        num_courses=args.courses,
        num_rooms=num_rooms,
        num_slots=args.slots,
        density=args.density,
        tightness=args.tightness,
        seed=args.seed,
    )

    summary = gen.generate(args.output_dir)

    print("\n  Instance generated successfully!")
    print(f"    Courses generated : {summary['num_courses']}")
    print(f"    Rooms generated   : {summary['num_rooms']}")
    print(f"    Slots generated   : {summary['num_slots']}")
    print(f"    Students          : {summary['num_students']}")
    print(f"    Conflict pairs    : {summary['conflict_pairs']}")
    print(f"\n  Files written to: {args.output_dir}/")
    print("    - courses.csv")
    print("    - rooms.csv")
    print("    - timeslots.csv")
    print("    - students.csv")
    print("    - instructor_availability.csv")
    print("\n  To solve this instance:")
    print(f"    python main.py --input-dir {args.output_dir} --algorithm mac")


def run_experiment(exp_id):
    """dispatch to the right experiment"""
    if exp_id == "1":
        experiment_1()
    elif exp_id == "2":
        experiment_2()
    elif exp_id == "3":
        experiment_3()
    elif exp_id == "4":
        experiment_4()
    elif exp_id == "all":
        run_all()
    else:
        print(f"[ERROR] Unknown experiment '{exp_id}'.")
        sys.exit(1)


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.experiment is not None:
        run_experiment(args.experiment)
        return

    if args.generate:
        run_generate(args)
        return

    if args.input_dir is not None:
        run_solve(args)
        return

    default_dir = os.path.join("instances", "small")
    if os.path.isdir(default_dir):
        print(f"  No mode specified. Running default solve on '{default_dir}'.")
        args.input_dir = default_dir
        run_solve(args)
    else:
        parser.print_help()
        print("\n  [TIP] Run with --input-dir instances/small --algorithm mac")
        print("        or   --generate --courses 10 --output-dir instances/test")


if __name__ == "__main__":
    main()