# Q1 — CSP University Timetabling
This is my solution for Question 1 where I modeled the university timetabling problem as a Constraint Satisfaction Problem (CSP). The goal is to assign each course section to a time slot and room while avoiding clashes (room clashes, instructor clashes, student clashes). I also included a small soft-score at the end based on instructor preferred slots.

---

## What the problem looks like (my CSP setup)

- Variables: each course section id from `courses.csv` (example: `CS101-01`)
- Domain: for each course, a list of possible `(slot_id, room_id)` pairs
- Unary pruning (done once before search): removes obviously impossible pairs, like wrong room feature, not enough capacity, wrong slot duration, and instructor not available (if availability file exists)
- Binary constraints (checked during search):
  - Room conflict: two courses can’t use the same room at the same time
  - Instructor conflict: same instructor can’t teach two courses at the same time
  - Student conflict: courses that share at least one student can’t be in the same time slot

---

## Project Structure

```
Q1_CSP/
│
├── csp.py # Core CSP framework (variables, domains, constraints)
├── timetable.py # Timetabling CSP: CSV parsing, domain pruning, constraint setup
├── algorithms.py # All 4 search algorithms
├── heuristics.py # MRV, Degree, LCV heuristics
├── metrics.py # Performance tracking, tables, matplotlib plots
├── generator.py # Random instance generator
├── experiments.py # All 4 experimental evaluations
├── main.py # Command-line interface
├── gui.py # Bonus GUI (Tkinter + matplotlib)
│
├── instances/
│   └── small/
│       ├── courses.csv
│       ├── rooms.csv
│       ├── timeslots.csv
│       ├── students.csv
│       └── instructor_availability.csv
│
├── results/ # Auto-created when experiments run
├── README.md
└── requirements.txt
```

---

## Setup

I recommend using a virtual environment, but it’s optional.

### 1) Create and activate venv (optional)
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

---

## How to run

### Solve the default small instance (recommended)
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

### Run experiments
```bash
python main.py --experiment 1
python main.py --experiment 2
python main.py --experiment 3
python main.py --experiment 4
python main.py --experiment all
```

### Launch the GUI (bonus)
```bash
python gui.py
```

---

## Algorithms implemented

- Backtracking
  - plain recursive backtracking with consistency checks
- Forward Checking
  - after assigning a variable, it prunes values from direct neighbours that no longer work
- MAC (AC-3)
  - after each assignment, it runs AC-3 style propagation to maintain arc consistency
- Min-Conflicts
  - local search, starts with a random full assignment and keeps repairing conflicted variables

---

## Heuristics implemented

Variable ordering:
- MRV: picks the course with the smallest remaining domain
- Degree: picks the course that is connected to the most other unassigned courses
- MRV + Degree: MRV first, degree as the tie-break

Value ordering:
- LCV: tries the value that blocks the fewest choices for neighbours

---

## Experiments

All experiments are in `experiments.py` and can be run from `main.py`.

1. Algorithm Comparison  
   Compares all 4 algorithms across multiple problem sizes.

2. Heuristic Impact  
   Uses MAC and compares heuristic combos like no heuristics vs MRV vs MRV+Degree vs MRV+Degree+LCV.

3. Phase Transition  
   Fixes the size and increases tightness (0.1 to 0.9) and shows when the problems start becoming mostly UNSAT.

4. Systematic vs Local Search  
   Compares MAC against Min-Conflicts on easy, medium, and hard instances.

Plots and summaries are saved in the `results/` folder.

---

## Required instructors

These are included as required by the assignment:

- Mr Aamir Gulzar  
- Mr Arshad Islam  
- Maam Marium Hida  
- Mr Anas Bin Rashid  
- Mr Hasnain Akhtar  
- Mr Hasan Mujtaba  
- Maam Bushra Kanwal  

Extra instructors can also be generated if the instance needs more.

---

## CSV files (what each one does)

- courses.csv  
  course section info, instructor, enrollment, duration, and required room feature

- rooms.csv  
  room info, capacity, and features (Lab, Projector, Whiteboard)

- timeslots.csv  
  time slots with days, start time, and duration

- students.csv  
  students and their enrolled courses (I use this to build the student conflict map)

- instructor_availability.csv  
  optional. if it exists, it limits instructors to only those slots

---

## Dependencies

See `requirements.txt`. Main ones are:

- matplotlib  
  used for saving experiment plots and for charts inside the GUI
- tkinter  
  GUI only

Everything else is standard Python libraries like `csv`, `os`, `time`, etc.
---

## Academic Integrity

All CSP modeling, algorithms (backtracking, forward checking, MAC, min-conflicts), heuristics, and experiments were implemented by me with the help of lectures. 

For the GUI/visual part (Tkinter layout and matplotlib embedding), I used AI help to speed up the interface work, but the CSP logic, constraints, and solving code are my own.