"""
timetable.py  --  build the university timetabling CSP from CSV files
"""

import csv
import os
from csp import CSP, Constraint


# basic CSV loaders
def load_courses(path):
    """read courses.csv -> {course_id: {name, instructor, enrollment, duration, features}}"""
    courses = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row["CourseID"].strip()
            courses[cid] = {
                "name": row["CourseName"].strip(),
                "instructor": row["Instructor"].strip(),
                "enrollment": int(row["Enrollment"].strip()),
                "duration": int(row["Duration"].strip()),
                "features": row["RoomFeatures"].strip(),
            }
    return courses


def load_rooms(path):
    """read rooms.csv -> {room_id: {building, capacity, features(set)}}"""
    rooms = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = row["RoomID"].strip()
            features_str = row["Features"]
            if features_str:
                parts = features_str.split(";")
            else:
                parts = []
            feature_list = []
            for x in parts:
                feature_list.append(x.strip())
            rooms[rid] = {
                "building": row["Building"].strip(),
                "capacity": int(row["Capacity"].strip()),
                "features": set(feature_list),
            }
    return rooms


def load_timeslots(path):
    """read timeslots.csv -> {slot_id: {days(list), start_time, duration}}"""
    slots = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row["SlotID"].strip()
            days_str = row["Days"]
            parts = days_str.split("/")
            days = []
            for d in parts:
                days.append(d.strip())
            slots[sid] = {
                "days": days,
                "start_time": row["StartTime"].strip(),
                "duration": int(row["Duration"].strip()),
            }
    return slots


def load_students(path):
    """
    read students.csv -> students dict and course conflict map
    students: {student_id: {name, courses(set)}}
    conflict_map: {course_id: set(other_course_ids)}
    """
    students = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row["StudentID"].strip()
            enrolled_str = row["EnrolledCourses"]
            parts = enrolled_str.split(";") if enrolled_str else []
            enrolled = []
            for c in parts:
                c2 = c.strip()
                if c2:
                    enrolled.append(c2)
            students[sid] = {
                "name": row["StudentName"].strip(),
                "courses": set(enrolled),
            }

    conflict_map = {}
    for sid, sdata in students.items():
        course_list = list(sdata["courses"])
        i = 0
        while i < len(course_list):
            j = i + 1
            while j < len(course_list):
                c1 = course_list[i]
                c2 = course_list[j]
                if c1 not in conflict_map:
                    conflict_map[c1] = set()
                if c2 not in conflict_map:
                    conflict_map[c2] = set()
                conflict_map[c1].add(c2)
                conflict_map[c2].add(c1)
                j += 1
            i += 1

    return students, conflict_map


def load_instructor_availability(path):
    """
    read instructor_availability.csv -> {instructor: {available:set, preferred:set}}
    return {} if file does not exist
    """
    if not os.path.exists(path):
        return {}

    availability = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            instructor = row["Instructor"].strip()
            avail_str = row["AvailableSlots"]
            pref_str = row["PreferredSlots"]

            if avail_str:
                avail_parts = avail_str.split(";")
            else:
                avail_parts = []
            available = set()
            for s in avail_parts:
                s2 = s.strip()
                if s2:
                    available.add(s2)

            if pref_str:
                pref_parts = pref_str.split(";")
            else:
                pref_parts = []
            preferred = set()
            for s in pref_parts:
                s2 = s.strip()
                if s2:
                    preferred.add(s2)

            availability[instructor] = {
                "available": available,
                "preferred": preferred,
            }
    return availability


def build_initial_domains(courses, rooms, timeslots):
    """initial domain: every (slot, room) combo for each course"""
    domains = {}
    for cid in courses:
        domain = []
        for slot_id in timeslots:
            for room_id in rooms:
                domain.append((slot_id, room_id))
        domains[cid] = domain
    return domains


def apply_unary_constraints(domains, courses, rooms, timeslots, availability):
    """
    basic pruning using single-course restrictions:
    room features, capacity, duration, instructor availability
    """
    pruned_total = 0

    for cid, domain in domains.items():
        course = courses[cid]
        required = course["features"]
        enrolled = course["enrollment"]
        duration = course["duration"]
        instructor = course["instructor"]

        to_remove = []
        for (slot_id, room_id) in domain:
            room = rooms[room_id]
            slot = timeslots[slot_id]

            if required not in room["features"]:
                to_remove.append((slot_id, room_id))
                continue

            if room["capacity"] < enrolled:
                to_remove.append((slot_id, room_id))
                continue

            if slot["duration"] != duration:
                to_remove.append((slot_id, room_id))
                continue

            if availability and instructor in availability:
                if slot_id not in availability[instructor]["available"]:
                    to_remove.append((slot_id, room_id))
                    continue

        for pair in to_remove:
            if pair in domain:
                domain.remove(pair)

        pruned_total += len(to_remove)

    return pruned_total


# simple binary constraint factories
def make_room_conflict_fn():
    """two courses cannot be in the same room at the same slot"""

    def check(assignment):
        vals = list(assignment.values())
        if len(vals) < 2:
            return True
        (slot1, room1) = vals[0]
        (slot2, room2) = vals[1]
        if room1 == room2 and slot1 == slot2:
            return False
        return True

    return check


def make_instructor_conflict_fn(courses):
    """instructor cannot teach two courses in the same slot"""

    def check(assignment):
        items = list(assignment.items())
        if len(items) < 2:
            return True
        (cid1, (slot1, _)) = items[0]
        (cid2, (slot2, _)) = items[1]
        if courses[cid1]["instructor"] == courses[cid2]["instructor"]:
            if slot1 == slot2:
                return False
        return True

    return check


def make_student_conflict_fn(conflict_map):
    """courses sharing students cannot be in the same slot"""

    def check(assignment):
        items = list(assignment.items())
        if len(items) < 2:
            return True
        (cid1, (slot1, _)) = items[0]
        (cid2, (slot2, _)) = items[1]
        if cid1 in conflict_map:
            if cid2 in conflict_map[cid1] and slot1 == slot2:
                return False
        return True

    return check


def make_room_capacity_conflict_fn(courses, rooms):
    """
    dummy room+capacity conflict (already handled by unary + room_conflict),
    kept here to match original structure
    """

    def check(assignment):
        items = list(assignment.items())
        if len(items) < 2:
            return True
        (cid1, (slot1, room1)) = items[0]
        (cid2, (slot2, room2)) = items[1]
        if slot1 == slot2 and room1 == room2:
            return False
        return True

    return check


def register_binary_constraints(csp, courses, rooms, conflict_map):
    """add all binary constraints between course pairs"""
    course_ids = list(courses.keys())
    n = len(course_ids)

    room_fn = make_room_conflict_fn()
    instructor_fn = make_instructor_conflict_fn(courses)
    student_fn = make_student_conflict_fn(conflict_map)
    capacity_fn = make_room_capacity_conflict_fn(courses, rooms)

    pairs_added = 0
    i = 0
    while i < n:
        j = i + 1
        while j < n:
            ci = course_ids[i]
            cj = course_ids[j]

            same_instructor = courses[ci]["instructor"] == courses[cj]["instructor"]
            share_students = cj in conflict_map.get(ci, set())

            csp.add_constraint(
                Constraint([ci, cj], room_fn, name=f"RoomConflict({ci},{cj})")
            )

            if same_instructor:
                csp.add_constraint(
                    Constraint(
                        [ci, cj],
                        instructor_fn,
                        name=f"InstructorConflict({ci},{cj})",
                    )
                )

            if share_students:
                csp.add_constraint(
                    Constraint(
                        [ci, cj],
                        student_fn,
                        name=f"StudentConflict({ci},{cj})",
                    )
                )

            pairs_added += 1
            j += 1
        i += 1

    return pairs_added


def build_timetabling_csp(input_dir):
    """
    full pipeline: load CSVs -> build domains -> prune -> build CSP + constraints
    """
    courses = load_courses(os.path.join(input_dir, "courses.csv"))
    rooms = load_rooms(os.path.join(input_dir, "rooms.csv"))
    timeslots = load_timeslots(os.path.join(input_dir, "timeslots.csv"))
    students, conflict_map = load_students(os.path.join(input_dir, "students.csv"))
    availability = load_instructor_availability(
        os.path.join(input_dir, "instructor_availability.csv")
    )

    domains = build_initial_domains(courses, rooms, timeslots)

    pruned = apply_unary_constraints(
        domains, courses, rooms, timeslots, availability
    )

    csp = CSP()
    for cid in courses:
        if len(domains[cid]) == 0:
            print(f"  [WARNING] '{cid}' has empty domain after pruning!")
        csp.add_variable(cid, domains[cid])

    pairs = register_binary_constraints(csp, courses, rooms, conflict_map)

    meta = {
        "pruned_values": pruned,
        "constraint_pairs": pairs,
        "num_courses": len(courses),
        "num_rooms": len(rooms),
        "num_slots": len(timeslots),
        "num_students": len(students),
        "conflict_map": conflict_map,
        "availability": availability,
    }

    return csp, courses, rooms, timeslots, students, availability, meta


def print_solution(
    solution,
    courses,
    rooms,
    timeslots,
    algorithm_name,
    metrics,
    soft_score=0,
):
    """pretty-print final timetable and metrics"""
    sep = "=" * 62
    dash = "-" * 40

    print(f"\n{sep}")
    print("         UNIVERSITY TIMETABLE SOLUTION")
    print(sep)
    print(f"  Algorithm : {algorithm_name}")
    if solution:
        print("  Status    : SOLUTION FOUND")
    else:
        print("  Status    : UNSATISFIABLE")
    print(sep)

    if not solution:
        print("\n  No solution could be found with the given constraints.")
        _print_metrics(metrics)
        return

    print("\nCOURSE SCHEDULE:")
    print(dash)
    for cid in sorted(solution.keys()):
        slot_id, room_id = solution[cid]
        course = courses[cid]
        room = rooms[room_id]
        slot = timeslots[slot_id]

        start = slot["start_time"]
        dur = slot["duration"]
        h = int(start.split(":")[0])
        m = int(start.split(":")[1])
        end_m = m + dur
        end_h = h + end_m // 60
        end_m = end_m % 60
        end_str = f"{end_h:02d}:{end_m:02d}"

        days_str = "/".join(slot["days"])

        print(f"\n  {cid}: {course['name']}")
        print(f"    Instructor : {course['instructor']}")
        print(f"    Time Slot  : {slot_id} ({days_str} {start}-{end_str})")
        print(
            f"    Room       : {room_id} ({room['building']}, "
            f"Capacity: {room['capacity']})"
        )
        print(f"    Enrolled   : {course['enrollment']}")

    print(f"\n{sep}")
    print("                  SCHEDULE GRID VIEW")
    print(sep)

    slot_ids = sorted(timeslots.keys())
    room_ids = sorted(rooms.keys())

    grid = {}
    for cid, pair in solution.items():
        slot_id, room_id = pair
        grid[(slot_id, room_id)] = cid

    col_w = 12
    header = f"{'Room':<8}"
    for s in slot_ids:
        header += f"{s:^{col_w}}"
    print(header)
    print("-" * len(header))

    for room_id in room_ids:
        row = f"{room_id:<8}"
        for slot_id in slot_ids:
            cell = grid.get((slot_id, room_id), "[EMPTY]")
            row += f"{cell:^{col_w}}"
        print(row)

    _print_metrics(metrics, soft_score)
    _print_warnings(solution, courses, rooms, timeslots)


def _print_metrics(metrics, soft_score=0):
    sep = "=" * 62
    print(f"\n{sep}")
    print("              PERFORMANCE METRICS")
    print(sep)
    total = metrics.get("total_courses", "?")
    scheduled = metrics.get("scheduled", "?")
    print(f"  Total Courses Scheduled : {scheduled}/{total}")
    print(f"  Variable Assignments    : {metrics.get('assignments', 0)}")
    print(f"  Backtracks              : {metrics.get('backtracks', 0)}")
    print(f"  Constraint Checks       : {metrics.get('constraint_checks', 0)}")
    print(
        "  Execution Time          : "
        f"{metrics.get('time', 0.0):.4f} seconds"
    )
    if soft_score:
        print(f"  Soft Constraint Score   : +{soft_score}")
    if metrics.get("valid", True):
        status = "All hard constraints satisfied"
    else:
        status = "CONSTRAINT VIOLATIONS DETECTED"
    print(f"  Solution Quality        : {status}")
    print(sep)


def _print_warnings(solution, courses, rooms, timeslots):
    """check for hard constraint violations (for debugging)"""
    warnings = []

    assigned_list = list(solution.items())
    n = len(assigned_list)

    i = 0
    while i < n:
        ci, (si, ri) = assigned_list[i]
        j = i + 1
        while j < n:
            cj, (sj, rj) = assigned_list[j]

            if si == sj and ri == rj:
                warnings.append(
                    f"ROOM CONFLICT: {ci} and {cj} both in {ri} at {si}"
                )

            if (
                courses[ci]["instructor"] == courses[cj]["instructor"]
                and si == sj
            ):
                msg = (
                    "INSTRUCTOR CONFLICT: "
                    f"{courses[ci]['instructor']} teaching {ci} and {cj} "
                    f"at the same time ({si})"
                )
                warnings.append(msg)

            j += 1
        i += 1

    for cid, (slot_id, room_id) in solution.items():
        enroll = courses[cid]["enrollment"]
        capacity = rooms[room_id]["capacity"]
        if enroll > capacity:
            warnings.append(
                f"CAPACITY VIOLATION: {cid} has {enroll} students "
                f"but {room_id} only holds {capacity}"
            )

    if warnings:
        print("\n  *** WARNINGS ***")
        for w in warnings:
            print(f"  [!] {w}")
    else:
        print("\n  No constraint violations detected. Schedule is valid.")


def compute_soft_score(solution, courses, availability):
    """+5 for each course in an instructor's preferred slot"""
    score = 0
    for cid, (slot_id, _) in solution.items():
        instructor = courses[cid]["instructor"]
        if instructor in availability:
            preferred = availability[instructor]["preferred"]
            if slot_id in preferred:
                score += 5
    return score