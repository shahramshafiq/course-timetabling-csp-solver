"""
generator.py  --  random CSP instance generator for the timetabling problem
"""

import csv
import os
import random
import math


# fixed name pools for Pakistani-style names
PAKISTANI_FIRST_NAMES_MALE = [
    "Ali", "Ahmed", "Hassan", "Usman", "Omar", "Bilal", "Hamza",
    "Zain", "Talha", "Farhan", "Asad", "Shahid", "Imran", "Tariq",
    "Kamran", "Salman", "Danish", "Faisal", "Rizwan", "Junaid",
    "Khaled", "Saad", "Waleed", "Yasir", "Adnan", "Babar", "Fahad",
    "Ghulam", "Irfan", "Jawad", "Kashif", "Luqman", "Moeen", "Naveed"
]

PAKISTANI_FIRST_NAMES_FEMALE = [
    "Fatima", "Ayesha", "Zainab", "Maryam", "Sara", "Hira", "Sana",
    "Nadia", "Amna", "Rabia", "Mahnoor", "Iqra", "Kiran", "Layla",
    "Mehwish", "Nimra", "Oria", "Pakeeza", "Qurat", "Rida",
    "Saima", "Tayyaba", "Ushna", "Veena", "Warda", "Zara"
]

PAKISTANI_LAST_NAMES = [
    "Ahmed", "Khan", "Malik", "Siddiqui", "Tariq", "Butt", "Chaudhry",
    "Qureshi", "Sheikh", "Akhtar", "Hussain", "Raza", "Baig", "Mirza",
    "Hashmi", "Abbasi", "Ansari", "Farooq", "Gilani", "Haider",
    "Javed", "Kazmi", "Lodhi", "Minhas", "Niazi", "Pirzada", "Rana",
    "Saeed", "Toor", "Waheed", "Yusuf", "Zahid", "Alvi", "Bhatti"
]

# 7 required instructors given in the assignment
REQUIRED_INSTRUCTORS = [
    "Mr Aamir Gulzar",
    "Mr Arshad Islam",
    "Maam Marium Hida",
    "Mr Anas Bin Rashid",
    "Mr Hasnain Akhtar",
    "Mr Hasan Mujtaba",
    "Maam Bushra Kanwal"
]

COURSE_PREFIXES = [
    "CS", "MATH", "ENG", "PHY", "EE", "SE", "AI", "DS",
    "NET", "SEC", "DB", "OS", "HCI", "ML", "CV"
]

COURSE_NAMES = [
    "Introduction to Programming", "Data Structures", "Algorithms",
    "Database Systems", "Operating Systems", "Computer Networks",
    "Software Engineering", "Artificial Intelligence", "Machine Learning",
    "Computer Vision", "Calculus I", "Calculus II", "Linear Algebra",
    "Discrete Mathematics", "Statistics", "Physics I", "Physics II",
    "Digital Logic", "Computer Architecture", "Compiler Design",
    "Theory of Computation", "Human Computer Interaction",
    "Parallel Computing", "Distributed Systems", "Cybersecurity",
    "Cloud Computing", "Mobile Development", "Web Engineering",
    "Numerical Methods", "Probability Theory", "English Composition",
    "Technical Writing", "Ethics in Computing", "Project Management",
    "Embedded Systems", "Signal Processing", "Image Processing",
    "Natural Language Processing", "Robotics", "Game Development",
    "Blockchain", "IoT Systems", "Data Mining", "Big Data Analytics",
    "Network Security", "Cryptography", "Information Retrieval",
    "Computer Graphics", "Scientific Computing", "Quantum Computing"
]

ROOM_FEATURES_OPTIONS = ["Lab", "Projector", "Whiteboard"]
BUILDINGS = [
    "CS Building", "Lab Building", "Main Building",
    "Engineering Block", "Science Block"
]


# simple name generator for students
def make_student_name(used=None):
    if used is None:
        used = set()

    attempts = 0
    while attempts < 200:
        attempts += 1
        gender = random.choice(["m", "f"])
        if gender == "m":
            first = random.choice(PAKISTANI_FIRST_NAMES_MALE)
        else:
            first = random.choice(PAKISTANI_FIRST_NAMES_FEMALE)
        last = random.choice(PAKISTANI_LAST_NAMES)
        name = f"{first} {last}"
        if name not in used:
            used.add(name)
            return name

    num = random.randint(1000, 9999)
    return f"Student{num}"


# simple name generator for extra instructors
def make_extra_instructor(index, used=None):
    if used is None:
        used = set()

    attempts = 0
    while attempts < 200:
        attempts += 1
        gender = random.choice(["mr", "maam"])
        if gender == "mr":
            first = random.choice(PAKISTANI_FIRST_NAMES_MALE)
        else:
            first = random.choice(PAKISTANI_FIRST_NAMES_FEMALE)
        last = random.choice(PAKISTANI_LAST_NAMES)
        title = "Mr" if gender == "mr" else "Maam"
        name = f"{title} {first} {last}"
        if name not in used:
            used.add(name)
            return name

    return f"Mr Instructor{index}"


class InstanceGenerator:
    """
    Creates one random instance and writes all CSVs for it.
    """

    def __init__(self, num_courses=10, num_rooms=8, num_slots=20,
                 density=0.3, tightness=0.3, seed=None):

        self.num_courses = num_courses
        self.num_rooms = max(1, num_rooms)
        self.num_slots = max(6, num_slots)
        self.density = density
        self.tightness = tightness

        if seed is not None:
            random.seed(seed)

        self.instructors = list(REQUIRED_INSTRUCTORS)
        used_names = set(REQUIRED_INSTRUCTORS)
        target = max(7, num_courses // 3)

        while len(self.instructors) < target:
            idx = len(self.instructors)
            extra = make_extra_instructor(idx, used_names)
            self.instructors.append(extra)

    # top-level generate function
    def generate(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)

        slots = self._generate_slots()
        rooms = self._generate_rooms(slots)
        courses = self._generate_courses(slots, rooms)
        students, conflict_map = self._generate_students(courses)
        avail = self._generate_availability(slots)

        self._write_timeslots(slots, os.path.join(output_dir, "timeslots.csv"))
        self._write_rooms(rooms, os.path.join(output_dir, "rooms.csv"))
        self._write_courses(courses, os.path.join(output_dir, "courses.csv"))
        self._write_students(students, os.path.join(output_dir, "students.csv"))
        self._write_availability(
            avail, os.path.join(output_dir, "instructor_availability.csv")
        )

        total_conflicts = 0
        for v in conflict_map.values():
            total_conflicts += len(v)
        total_conflicts = total_conflicts // 2

        summary = {
            "output_dir": output_dir,
            "num_courses": len(courses),
            "num_rooms": len(rooms),
            "num_slots": len(slots),
            "num_students": len(students),
            "density": self.density,
            "tightness": self.tightness,
            "conflict_pairs": total_conflicts,
        }
        return summary

    # create time slots
    def _generate_slots(self):
        slots = {}

        effective = int(self.num_slots * (1.0 - self.tightness * 0.4))
        if effective < 4:
            effective = 4

        mwf_starts = [
            "08:00", "09:00", "10:00", "11:00",
            "12:00", "13:00", "14:00", "15:00", "16:00",
        ]
        tth_starts = [
            "08:00", "09:30", "11:00", "12:30",
            "14:00", "15:30", "17:00",
        ]

        count = 0
        for start in mwf_starts:
            if count >= effective:
                break
            sid = "MWF-" + start.replace(":", "")
            slots[sid] = {
                "days": ["Monday", "Wednesday", "Friday"],
                "start_time": start,
                "duration": 50,
            }
            count += 1

        for start in tth_starts:
            if count >= effective:
                break
            sid = "TTh-" + start.replace(":", "")
            slots[sid] = {
                "days": ["Tuesday", "Thursday"],
                "start_time": start,
                "duration": 75,
            }
            count += 1

        return slots

    # create rooms
    def _generate_rooms(self, slots):
        rooms = {}

        features_pool = [
            {"Lab", "Projector", "Whiteboard"},
            {"Projector", "Whiteboard"},
            {"Whiteboard"},
            {"Lab", "Projector"},
            {"Projector"},
        ]

        i = 0
        while i < self.num_rooms:
            rid = "R" + str(100 + i)
            building = random.choice(BUILDINGS)

            base_cap = random.randint(30, 80)
            if self.tightness > 0.5:
                base_cap = random.randint(25, 50)

            feats = random.choice(features_pool)
            rooms[rid] = {
                "building": building,
                "capacity": base_cap,
                "features": feats,
            }
            i += 1

        return rooms

    # create courses
    def _generate_courses(self, slots, rooms):
        courses = {}
        used_ids = set()
        name_pool = list(COURSE_NAMES)
        random.shuffle(name_pool)

        durations = [50, 75]
        all_features = ["Lab", "Projector", "Whiteboard"]

        max_cap = 0
        for r in rooms.values():
            if r["capacity"] > max_cap:
                max_cap = r["capacity"]

        i = 0
        while i < self.num_courses:
            if name_pool:
                name = name_pool.pop(0)
            else:
                name = "Advanced Topic " + str(i + 1)

            prefix = random.choice(COURSE_PREFIXES)
            number = random.randint(100, 499)
            cid = f"{prefix}{number}-{i+1:02d}"
            while cid in used_ids:
                number = random.randint(100, 499)
                cid = f"{prefix}{number}-{i+1:02d}"
            used_ids.add(cid)

            instructor = random.choice(self.instructors)
            duration = random.choice(durations)
            feature = random.choice(all_features)

            if self.tightness <= 0.3:
                hi = int(max_cap * 0.6)
            elif self.tightness <= 0.5:
                hi = int(max_cap * 0.8)
            else:
                hi = max_cap

            if hi < 15:
                hi = 15
            enrollment = random.randint(15, hi)
            if enrollment > 100:
                enrollment = 100

            courses[cid] = {
                "name": name,
                "instructor": instructor,
                "enrollment": enrollment,
                "duration": duration,
                "features": feature,
            }
            i += 1

        return courses

    # create students and enrollments
    def _generate_students(self, courses):
        course_ids = list(courses.keys())
        ratio = density_to_student_ratio(self.density)
        num_students = int(len(course_ids) * ratio)
        if num_students < 5:
            num_students = 5

        students = {}
        used_names = set()
        conflict_map = {}

        i = 0
        while i < num_students:
            sid = f"{i+1:03d}"
            name = make_student_name(used_names)

            max_courses = 5
            if len(course_ids) < 5:
                max_courses = len(course_ids)
            num_enroll = random.randint(2, max_courses)

            enrolled = random.sample(course_ids, num_enroll)
            students[sid] = {
                "name": name,
                "courses": set(enrolled),
            }

            a = 0
            while a < len(enrolled):
                b = a + 1
                while b < len(enrolled):
                    c1 = enrolled[a]
                    c2 = enrolled[b]
                    if c1 not in conflict_map:
                        conflict_map[c1] = set()
                    if c2 not in conflict_map:
                        conflict_map[c2] = set()
                    conflict_map[c1].add(c2)
                    conflict_map[c2].add(c1)
                    b += 1
                a += 1

            i += 1

        return students, conflict_map

    # create instructor availability
    def _generate_availability(self, slots):
        slot_ids = list(slots.keys())
        availability = {}

        for instructor in self.instructors:
            frac = random.uniform(0.6, 0.9)
            num_avail = int(len(slot_ids) * frac)
            if num_avail < 2:
                num_avail = 2
            if num_avail > len(slot_ids):
                num_avail = len(slot_ids)

            available = set(random.sample(slot_ids, num_avail))

            num_pref = len(available) // 2
            if num_pref < 1:
                num_pref = 1

            preferred = set(random.sample(list(available), num_pref))

            availability[instructor] = {
                "available": available,
                "preferred": preferred,
            }

        return availability

    # csv writers
    def _write_timeslots(self, slots, path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["SlotID", "Days", "StartTime", "Duration"])
            for sid, data in slots.items():
                days_str = "/".join(data["days"])
                writer.writerow([sid, days_str, data["start_time"], data["duration"]])

    def _write_rooms(self, rooms, path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["RoomID", "Building", "Capacity", "Features"])
            for rid, data in rooms.items():
                feats = sorted(list(data["features"]))
                feats_str = ";".join(feats)
                writer.writerow([rid, data["building"], data["capacity"], feats_str])

    def _write_courses(self, courses, path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "CourseID",
                    "CourseName",
                    "Instructor",
                    "Enrollment",
                    "Duration",
                    "RoomFeatures",
                ]
            )
            for cid, data in courses.items():
                writer.writerow(
                    [
                        cid,
                        data["name"],
                        data["instructor"],
                        data["enrollment"],
                        data["duration"],
                        data["features"],
                    ]
                )

    def _write_students(self, students, path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["StudentID", "StudentName", "EnrolledCourses"])
            for sid, data in students.items():
                courses_sorted = sorted(list(data["courses"]))
                joined = ";".join(courses_sorted)
                writer.writerow([sid, data["name"], joined])

    def _write_availability(self, availability, path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Instructor", "AvailableSlots", "PreferredSlots"])
            for instructor, data in availability.items():
                avail_sorted = sorted(list(data["available"]))
                pref_sorted = sorted(list(data["preferred"]))
                avail_str = ";".join(avail_sorted)
                pref_str = ";".join(pref_sorted)
                writer.writerow([instructor, avail_str, pref_str])


def density_to_student_ratio(density):
    """
    simple linear mapping from density [0,1] to student/course ratio
    """
    return 1.0 + density * 2.5


def generate_instances(configs, base_dir="instances"):
    """
    create many instances according to config list
    """
    results = []
    i = 0
    while i < len(configs):
        cfg = configs[i]
        num_courses = cfg.get("courses", 10)

        rooms_val = cfg.get("rooms", None)
        if rooms_val is None:
            num_rooms = int(num_courses * 0.7)
            if num_rooms < 1:
                num_rooms = 1
        else:
            num_rooms = rooms_val

        num_slots = cfg.get("slots", 20)
        density = cfg.get("density", 0.3)
        tightness = cfg.get("tightness", 0.3)
        seed = cfg.get("seed", i * 42)

        folder_name = (
            f"c{num_courses}_r{num_rooms}_s{num_slots}"
            f"_d{int(density*10)}_t{int(tightness*10)}"
            f"_seed{seed}"
        )
        out_dir = os.path.join(base_dir, folder_name)

        gen = InstanceGenerator(
            num_courses=num_courses,
            num_rooms=num_rooms,
            num_slots=num_slots,
            density=density,
            tightness=tightness,
            seed=seed,
        )
        summary = gen.generate(out_dir)
        results.append((out_dir, summary))

        print(
            f"  [Generated] {out_dir}  "
            f"({num_courses} courses, {num_rooms} rooms, "
            f"{num_slots} slots, density={density}, tightness={tightness})"
        )

        i += 1

    return results


EXPERIMENT_1_CONFIGS = [
    {"courses": 10, "rooms": 8, "slots": 20, "density": 0.3, "tightness": 0.3},
    {"courses": 20, "rooms": 16, "slots": 30, "density": 0.5, "tightness": 0.5},
    {"courses": 30, "rooms": 24, "slots": 40, "density": 0.5, "tightness": 0.5},
    {"courses": 50, "rooms": 40, "slots": 50, "density": 0.7, "tightness": 0.7},
]


def get_phase_transition_configs(tightness_vals=None):
    """
    configs for experiment 3: fixed size, different tightness values
    """
    if tightness_vals is None:
        tightness_vals = []
        x = 1
        while x < 10:
            tightness_vals.append(round(x * 0.1, 1))
            x += 1

    configs = []
    for t in tightness_vals:
        cfg = {
            "courses": 20,
            "rooms": 16,
            "slots": 30,
            "density": 0.5,
            "tightness": t,
        }
        configs.append(cfg)
    return configs