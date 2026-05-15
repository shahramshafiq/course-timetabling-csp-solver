# CSP-based University Course Timetabling Solver

This repository provides a Constraint Satisfaction Problem (CSP) based solver for managing university course timetabling. The goal is to optimally assign each course section to a time slot and room, while respecting physical constraints (room features/capacities) and minimizing schedule conflicts for students and instructors. The code is modular, well-structured, and scalable for custom timetabling needs.

---

## Features

- Robust CSP framework for flexible timetabling
- Multiple search algorithms: Backtracking, Forward Checking, MAC (AC-3), and Min-Conflicts local search
- Powerful heuristics for efficient solving (MRV, Degree, LCV, etc.)
- Customizable via CSV input files for courses, rooms, timeslots, students, and (optionally) instructor availability
- Command-line interface for running solver and generating random instance data
- GUI built with Tkinter and Matplotlib for visualization

---

## Problem Modeling

- **Variables**: Each course section ID (e.g., `CS101-01`)
- **Domain**: For each section, a list of possible `(slot_id, room_id)` assignment pairs
- **Constraints:**
  - Unary: Exclude clearly invalid assignments (e.g., wrong room features, insufficient capacity, instructor unavailable)
  - Binary: Prevent conflicts such as
    - Room conflict: No two classes in same room at the same time
    - Instructor conflict: No instructor double-booked
    - Student conflict: Students attending multiple courses can't have overlapping classes

---

## Project Structure

```
CSP/
│
├── csp.py              # Core CSP framework (variables, domains, constraints)
├── timetable.py        # Timetabling CSP: CSV parsing, domain pruning, constraint setup
├── algorithms.py       # All search algorithms
├── heuristics.py       # MRV, Degree, LCV heuristics
├── metrics.py          # Performance tracking, tables, and plotting
├── generator.py        # Random instance generator
├── main.py             # Command-line interface
├── gui.py              # GUI application (Tkinter + Matplotlib)
│
├── instances/
│   └── small/
│       ├── courses.csv
│       ├── rooms.csv
│       ├── timeslots.csv
│       ├── students.csv
│       └── instructor_availability.csv
│
├── README.md
└── requirements.txt
```

---

## Getting Started

### 1. Optional: Create and activate a virtual environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

---

## Usage

### Solve the default sample instance
```bash
python main.py --input-dir instances/small --algorithm mac
```

### Try other algorithms
```bash
python main.py --input-dir instances/small --algorithm backtrack
python main.py --input-dir instances/small --algorithm fc
python main.py --input-dir instances/small --algorithm min_conflicts
```

### Use specific heuristics
```bash
python main.py --input-dir instances/small --algorithm mac --var-heuristic mrv_degree --val-heuristic lcv
```

### Generate a new random instance
```bash
python main.py --generate --courses 20 --rooms 16 --slots 30 --density 0.5 --tightness 0.5 --output-dir instances/medium
```

### Launch the GUI
```bash
python gui.py
```

---

## Algorithms

- **Backtracking:** Recursive backtracking with built-in consistency checks.
- **Forward Checking:** Prunes domains of affected variables after each assignment.
- **MAC (AC-3):** Maintains arc consistency during search for enhanced efficiency.
- **Min-Conflicts:** Local search, starts with a random full assignment and resolves conflicts iteratively.

---

## Heuristics

**Variable Ordering:**
- MRV (Minimum Remaining Values): Prioritizes the variable with the fewest legal options.
- Degree: Selects variable most constrained by unassigned neighbors.
- MRV + Degree: MRV as primary, Degree as tie-breaker.

**Value Ordering:**
- LCV (Least Constraining Value): Prefers the value that rules out the fewest choices for neighbors.

---

## CSV Input Files

- **courses.csv:** Course section info, instructor, enrollment, session duration, and required room feature.
- **rooms.csv:** Room data, capacity, and features (e.g., Lab, Projector, Whiteboard).
- **timeslots.csv:** Time slot IDs, days, start times, durations.
- **students.csv:** Student IDs and their enrolled courses.
- **instructor_availability.csv (optional):** Limits instructors to available time slots if provided.

---

## Dependencies

The main dependencies are:

- `matplotlib`: For charts and GUI plotting.
- `tkinter`: Used for the GUI.

All other code uses the Python standard library (`csv`, `os`, `time`, etc.). See `requirements.txt` for details.

---

## Instructors (Sample Data)

Example instructors included in the provided sample data:

- Mr Aamir Gulzar
- Mr Arshad Islam
- Maam Marium Hida
- Mr Anas Bin Rashid
- Mr Hasnain Akhtar
- Mr Hasan Mujtaba
- Maam Bushra Kanwal

Extra instructors can be generated when needed.
