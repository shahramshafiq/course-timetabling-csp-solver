<div align="center">

# Course Timetabling CSP Solver

Course timetabling modelled as a constraint satisfaction problem, with four search algorithms and a Tkinter visualiser.

![Python](https://img.shields.io/badge/Python-3-3776AB?style=flat-square&logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-2E7D32?style=flat-square)
![Matplotlib](https://img.shields.io/badge/Matplotlib-Charts-11557C?style=flat-square)
![CSP](https://img.shields.io/badge/Domain-Constraint%20Satisfaction-4B5563?style=flat-square)

</div>

## Overview

Assigning university courses to time slots and rooms without clashes is a constraint satisfaction problem. This project treats each course section as a variable whose domain is the set of feasible (time slot, room) pairs, then searches for a complete assignment that avoids room, instructor and student conflicts. Instances are read from CSV files, and the solver can be driven from the command line or from a Tkinter desktop app.

## Key Features

- Four search algorithms behind one `solve()` entry point: backtracking, forward checking, MAC (AC-3) and min-conflicts local search.
- Pluggable heuristics: variable ordering (static, MRV, degree, MRV with degree tie-break, random) and value ordering (static, LCV, random).
- Constraint model built from data: unary pruning on room features, room capacity, slot duration and instructor availability, plus binary constraints for room, instructor and student clashes.
- CSV-driven input for courses, rooms, time slots, students and optional instructor availability; each course placed in an instructor's preferred slot adds +5 to a reported soft score.
- Random instance generator with settings for course, room and slot counts, constraint density, tightness and a seed.
- Run metrics (assignments, backtracks, constraint checks, execution time) and a post-solve check that reports room, instructor and capacity violations.
- Tkinter app with a colour-coded schedule grid, a step-through animation of the search, run statistics and a built-in CSV editor.

## Tech Stack

| Area | Technology |
| --- | --- |
| Language | Python 3 |
| Search and heuristics | Hand-written backtracking, forward checking, MAC (AC-3), min-conflicts, MRV, degree, LCV |
| Desktop UI | Tkinter (ttk, Canvas, Treeview) |
| Charts | Matplotlib (optional) |
| Data | CSV files read with the `csv` module |
| Command line | `argparse` |

## Project Structure

```text
.
|-- main.py            # CLI: solve an instance, generate instances, run experiments
|-- gui.py             # Tkinter app: schedule grid, search animation, stats, CSV editor
|-- csp.py             # Generic CSP: variables, domains, constraints, consistency helpers
|-- timetable.py       # CSV loaders, domain pruning, timetabling constraints, result printing
|-- algorithms.py      # Backtracking, forward checking, MAC (AC-3), min-conflicts
|-- heuristics.py      # MRV, degree, LCV and static/random orderings
|-- generator.py       # Random instance generator
|-- experiments.py     # Benchmark experiments and plots
|-- metrics.py         # Run metrics, result tables, Matplotlib charts
|-- requirements.txt
`-- instances/small/   # Sample instance: five CSV files
```

## Getting Started

### Prerequisites

- Python 3 with Tkinter (needed only for the GUI; it ships with most Python installers)
- pip

No environment variables or API keys are required.

### Installation

```bash
git clone https://github.com/shahramshafiq/course-timetabling-csp-solver.git
cd course-timetabling-csp-solver

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Run

```bash
# Solve the bundled sample instance with MAC
python main.py --input-dir instances/small --algorithm mac

# Launch the desktop app
python gui.py
```

Running `python main.py` with no arguments solves `instances/small` using the defaults.

## Usage

Choose the algorithm and heuristics from the command line:

```bash
python main.py --input-dir instances/small --algorithm backtrack
python main.py --input-dir instances/small --algorithm fc
python main.py --input-dir instances/small --algorithm min_conflicts --mc-steps 10000 --seed 42
python main.py --input-dir instances/small --algorithm mac --var-heuristic mrv_degree --val-heuristic lcv
```

Generate a random instance, then solve it:

```bash
python main.py --generate --courses 20 --rooms 16 --slots 30 --density 0.5 --tightness 0.5 --output-dir instances/medium
python main.py --input-dir instances/medium --algorithm mac
```

Options:

| Option | Values | Default |
| --- | --- | --- |
| `--algorithm` | `backtrack`, `fc`, `mac`, `min_conflicts` (aliases `bt`, `forward_checking`, `ac3`, `mc`) | `mac` |
| `--var-heuristic` | `none`, `mrv`, `degree`, `mrv_degree`, `random` | `mrv_degree` |
| `--val-heuristic` | `none`, `lcv`, `random` | `lcv` |
| `--mc-steps` | maximum min-conflicts steps | `10000` |
| `--seed` | random seed for min-conflicts and the generator | none |
| `--experiment` | `1`, `2`, `3`, `4`, `all` | none |

A solve prints each course with its instructor, slot and room, a room-by-slot grid, and the run metrics. An instance is expected to contain `courses.csv`, `rooms.csv`, `timeslots.csv` and `students.csv`; `instructor_availability.csv` is optional.

The phase-transition experiment (`python main.py --experiment 3`) generates instances under `instances/tmp_exp/` and saves a plot to `results/exp3_phase_transition.png`.

## Limitations and Roadmap

- Preferred instructor slots only feed a soft score computed after the search. The solver returns the first complete assignment it finds and does not optimise that score.
- Each course occupies exactly one (slot, room) pair, and the slot length must equal the course duration. Slots carry their own day pattern (for example MWF or TTh), so there is no support for courses split across several sessions.
- Constraint lookups scan the full constraint list and every course pair gets a room constraint, so large instances are slow. There is no automated test suite yet.
- The benchmark runner behind `--experiment` needs a fix: experiments 1, 2 and 4 read a `success` field that the solver does not return. Experiment 3 does not use that code.

## Author

**Shahram Shafiq** - [GitHub](https://github.com/shahramshafiq) | [LinkedIn](https://www.linkedin.com/in/shahramshafiq/)
