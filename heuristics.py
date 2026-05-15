"""
heuristics.py  --  variable and value ordering helpers for CSP search
"""

import random


# variable ordering: MRV
def mrv(csp, assignment):
    """pick unassigned variable with the smallest domain"""
    unassigned = csp.get_unassigned(assignment)
    best_var = None
    best_size = float("inf")

    for var in unassigned:
        size = csp.domain_size(var)
        if size < best_size:
            best_size = size
            best_var = var

    return best_var


# variable ordering: degree heuristic
def degree_heuristic(csp, assignment):
    """pick unassigned variable with most constraints to other unassigned vars"""
    unassigned = set(csp.get_unassigned(assignment))

    best_var = None
    best_degree = -1

    for var in unassigned:
        degree = 0
        for nb in csp.neighbors[var]:
            if nb in unassigned:
                degree += 1
        if degree > best_degree:
            best_degree = degree
            best_var = var

    return best_var


# variable ordering: MRV + degree tie-break
def mrv_degree(csp, assignment):
    """MRV first, and if tie, use degree heuristic to break ties"""
    unassigned = csp.get_unassigned(assignment)
    if not unassigned:
        return None

    min_size = None
    for v in unassigned:
        size = csp.domain_size(v)
        if min_size is None or size < min_size:
            min_size = size

    candidates = []
    for v in unassigned:
        if csp.domain_size(v) == min_size:
            candidates.append(v)

    if len(candidates) == 1:
        return candidates[0]

    unassigned_set = set(unassigned)
    best_var = None
    best_degree = -1

    for var in candidates:
        degree = 0
        for nb in csp.neighbors[var]:
            if nb in unassigned_set:
                degree += 1
        if degree > best_degree:
            best_degree = degree
            best_var = var

    return best_var


# value ordering: LCV
def lcv(csp, var, assignment):
    """least constraining value: fewer future conflicts is better"""

    def conflict_count(value):
        return csp.count_conflicts(var, value, assignment)

    values = list(csp.domains[var])
    # manual sort using simple loop (instead of one-liner)
    values_with_score = []
    for v in values:
        score = conflict_count(v)
        values_with_score.append((score, v))

    values_with_score.sort(key=lambda p: p[0])

    ordered = []
    for score, v in values_with_score:
        ordered.append(v)
    return ordered


# no-heuristic variable order
def no_var_heuristic(csp, assignment):
    """static order: just follow variable list"""
    unassigned = csp.get_unassigned(assignment)
    if unassigned:
        return unassigned[0]
    return None


# no-heuristic value order
def no_val_heuristic(csp, var, assignment):
    """return domain as-is"""
    return list(csp.domains[var])


# random variable choice
def random_var_heuristic(csp, assignment):
    """pick a random unassigned variable"""
    unassigned = csp.get_unassigned(assignment)
    if not unassigned:
        return None
    return random.choice(unassigned)


# random value order
def random_val_heuristic(csp, var, assignment):
    """shuffle domain randomly"""
    values = list(csp.domains[var])
    random.shuffle(values)
    return values


# lookup helper for variable heuristics
def get_var_heuristic(name):
    name = name.lower().strip()
    options = {
        "none": no_var_heuristic,
        "static": no_var_heuristic,
        "mrv": mrv,
        "degree": degree_heuristic,
        "mrv_degree": mrv_degree,
        "random": random_var_heuristic,
    }
    if name not in options:
        raise ValueError(
            f"Unknown variable heuristic '{name}'. "
            f"Choose from: {list(options.keys())}"
        )
    return options[name]


# lookup helper for value heuristics
def get_val_heuristic(name):
    name = name.lower().strip()
    options = {
        "none": no_val_heuristic,
        "lcv": lcv,
        "random": random_val_heuristic,
    }
    if name not in options:
        raise ValueError(
            f"Unknown value heuristic '{name}'. "
            f"Choose from: {list(options.keys())}"
        )
    return options[name]