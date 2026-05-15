"""
algorithms.py  --  All four CSP search algorithms for course scheduling.
"""

import time
import random
import copy


# helper: pick first unassigned variable (no fancy heuristic)
def _pick_unassigned(csp, assignment):
    for v in csp.variables:
        if v not in assignment:
            return v
    return None


# helper: return domain values as-is
def _order_domain(csp, var, assignment):
    return list(csp.domains[var])


# Algorithm 1: Basic Backtracking Search
def backtracking_search(csp, var_heuristic=None, val_heuristic=None):
    """plain backtracking, no domain pruning during search"""
    csp.reset_stats()
    metrics = {
        'assignments': 0,
        'backtracks': 0,
        'algorithm': 'Backtracking'
    }
    start = time.time()

    solution = _bt_recursive({}, csp, var_heuristic, val_heuristic, metrics)

    metrics['time'] = time.time() - start
    metrics['constraint_checks'] = csp.constraint_checks
    metrics['scheduled'] = len(solution) if solution else 0
    metrics['total_courses'] = len(csp.variables)
    metrics['valid'] = solution is not None

    return solution, metrics


def _bt_recursive(assignment, csp, var_h, val_h, metrics):
    """recursive helper for backtracking"""
    if csp.is_complete(assignment):
        return assignment

    if var_h is not None:
        var = var_h(csp, assignment)
    else:
        var = _pick_unassigned(csp, assignment)

    if val_h is not None:
        values = val_h(csp, var, assignment)
    else:
        values = _order_domain(csp, var, assignment)

    for value in values:
        metrics['assignments'] += 1
        if csp.is_consistent(var, value, assignment):
            assignment[var] = value
            result = _bt_recursive(assignment, csp, var_h, val_h, metrics)
            if result is not None:
                return result
            del assignment[var]
            metrics['backtracks'] += 1

    return None


# Algorithm 2: Forward Checking
def forward_checking(csp, var_heuristic=None, val_heuristic=None):
    """backtracking plus forward checking to prune neighbours"""
    csp.reset_stats()
    metrics = {
        'assignments': 0,
        'backtracks': 0,
        'algorithm': 'Forward Checking'
    }
    start = time.time()

    solution = _fc_recursive({}, csp, var_heuristic, val_heuristic, metrics)

    metrics['time'] = time.time() - start
    metrics['constraint_checks'] = csp.constraint_checks
    metrics['scheduled'] = len(solution) if solution else 0
    metrics['total_courses'] = len(csp.variables)
    metrics['valid'] = solution is not None

    return solution, metrics


def _fc_recursive(assignment, csp, var_h, val_h, metrics):
    """recursive helper for forward checking"""
    if csp.is_complete(assignment):
        return assignment

    if var_h is not None:
        var = var_h(csp, assignment)
    else:
        var = _pick_unassigned(csp, assignment)

    if val_h is not None:
        values = val_h(csp, var, assignment)
    else:
        values = _order_domain(csp, var, assignment)

    for value in values:
        metrics['assignments'] += 1
        if not csp.is_consistent(var, value, assignment):
            metrics['backtracks'] += 1
            continue

        saved_domains = csp.copy_domains()
        assignment[var] = value

        domain_wiped = False
        for nb in csp.neighbors[var]:
            if nb in assignment:
                continue

            to_remove = []
            for nb_val in csp.domains[nb]:
                csp.constraint_checks += 1
                test = {}
                for k, v in assignment.items():
                    test[k] = v
                test[nb] = nb_val

                valid_for_all = True
                constraints = csp.get_binary_constraints(var, nb)
                for c in constraints:
                    csp.constraint_checks += 1
                    if not c.is_satisfied(test):
                        valid_for_all = False
                        break

                if not valid_for_all:
                    to_remove.append(nb_val)

            for v in to_remove:
                csp.domains[nb].remove(v)

            if len(csp.domains[nb]) == 0:
                domain_wiped = True
                break

        if not domain_wiped:
            result = _fc_recursive(assignment, csp, var_h, val_h, metrics)
            if result is not None:
                return result

        del assignment[var]
        csp.restore_domains(saved_domains)
        metrics['backtracks'] += 1

    return None


# Algorithm 3: MAC (Maintaining Arc Consistency with AC-3)
def mac_search(csp, var_heuristic=None, val_heuristic=None):
    """backtracking plus AC-3 after each assignment"""
    csp.reset_stats()
    metrics = {
        'assignments': 0,
        'backtracks': 0,
        'algorithm': 'MAC (AC-3)'
    }
    start = time.time()

    solution = _mac_recursive({}, csp, var_heuristic, val_heuristic, metrics)

    metrics['time'] = time.time() - start
    metrics['constraint_checks'] = csp.constraint_checks
    metrics['scheduled'] = len(solution) if solution else 0
    metrics['total_courses'] = len(csp.variables)
    metrics['valid'] = solution is not None

    return solution, metrics


def _mac_recursive(assignment, csp, var_h, val_h, metrics):
    """recursive helper for MAC"""
    if csp.is_complete(assignment):
        return assignment

    if var_h is not None:
        var = var_h(csp, assignment)
    else:
        var = _pick_unassigned(csp, assignment)

    if val_h is not None:
        values = val_h(csp, var, assignment)
    else:
        values = _order_domain(csp, var, assignment)

    for value in values:
        metrics['assignments'] += 1
        if not csp.is_consistent(var, value, assignment):
            metrics['backtracks'] += 1
            continue

        saved_domains = csp.copy_domains()
        assignment[var] = value

        csp.domains[var] = [value]
        ok = _ac3(csp, start_var=var, assignment=assignment)

        if ok:
            result = _mac_recursive(assignment, csp, var_h, val_h, metrics)
            if result is not None:
                return result

        del assignment[var]
        csp.restore_domains(saved_domains)
        metrics['backtracks'] += 1

    return None


def _ac3(csp, start_var, assignment):
    """AC-3 starting from arcs related to start_var"""
    queue = []
    for nb in csp.neighbors[start_var]:
        if nb not in assignment:
            queue.append((nb, start_var))

    while len(queue) > 0:
        xi, xj = queue.pop(0)

        changed = _revise(csp, xi, xj, assignment)
        if changed:
            if len(csp.domains[xi]) == 0:
                return False
            for xk in csp.neighbors[xi]:
                if xk != xj and xk not in assignment:
                    queue.append((xk, xi))

    return True


def _revise(csp, xi, xj, assignment):
    """make xi arc-consistent w.r.t xj"""
    revised = False
    constraints = csp.get_binary_constraints(xi, xj)
    if not constraints:
        return False

    to_remove = []

    for xi_val in csp.domains[xi]:
        supported = False

        if xj in assignment:
            xj_domain = [assignment[xj]]
        else:
            xj_domain = list(csp.domains[xj])

        for xj_val in xj_domain:
            test = {xi: xi_val, xj: xj_val}
            consistent = True
            for c in constraints:
                csp.constraint_checks += 1
                if not c.is_satisfied(test):
                    consistent = False
                    break
            if consistent:
                supported = True
                break

        if not supported:
            to_remove.append(xi_val)
            revised = True

    for v in to_remove:
        csp.domains[xi].remove(v)

    return revised


# Algorithm 4: Min-Conflicts Local Search
def min_conflicts(csp, max_steps=10000, random_seed=None):
    """local search using min-conflicts heuristic"""
    if random_seed is not None:
        random.seed(random_seed)

    csp.reset_stats()
    metrics = {
        'assignments': 0,
        'backtracks': 0,
        'algorithm': 'Min-Conflicts'
    }
    start = time.time()

    assignment = _random_complete_assignment(csp)
    metrics['assignments'] += len(csp.variables)

    step = 0
    while step < max_steps:
        step += 1
        conflicted = csp.get_conflicted_vars(assignment)

        if not conflicted:
            metrics['time'] = time.time() - start
            metrics['constraint_checks'] = csp.constraint_checks
            metrics['scheduled'] = len(assignment)
            metrics['total_courses'] = len(csp.variables)
            metrics['valid'] = True
            metrics['steps'] = step - 1
            return assignment, metrics

        var = random.choice(conflicted)

        best_val = None
        best_count = float('inf')

        for value in csp.domains[var]:
            count = csp.conflicts_count(var, value, assignment)
            if count < best_count:
                best_count = count
                best_val = value
            else:
                if count == best_count and random.random() < 0.1:
                    best_val = value

        assignment[var] = best_val
        metrics['assignments'] += 1

    metrics['time'] = time.time() - start
    metrics['constraint_checks'] = csp.constraint_checks
    metrics['scheduled'] = 0
    metrics['total_courses'] = len(csp.variables)
    metrics['valid'] = False
    metrics['steps'] = max_steps

    return None, metrics


def _random_complete_assignment(csp):
    """assign each variable a random value from its domain"""
    assignment = {}
    for var in csp.variables:
        domain = csp.domains[var]
        if domain:
            assignment[var] = random.choice(domain)
        else:
            assignment[var] = None
    return assignment


# Unified Solver Interface
def solve(csp, algorithm='mac', var_heuristic=None, val_heuristic=None,
          mc_steps=10000, seed=None):
    """single entry point that picks which algorithm to run"""
    algo = algorithm.lower()
    algo = algo.replace('-', '_')
    algo = algo.replace(' ', '_')

    if algo == 'backtrack' or algo == 'bt' or algo == 'backtracking':
        return backtracking_search(csp, var_heuristic, val_heuristic)

    if algo == 'fc' or algo == 'forward_checking' or algo == 'forward':
        return forward_checking(csp, var_heuristic, val_heuristic)

    if algo == 'mac' or algo == 'ac3' or algo == 'ac_3' or algo == 'ac-3':
        return mac_search(csp, var_heuristic, val_heuristic)

    if algo == 'min_conflicts' or algo == 'minconflicts' or algo == 'mc' or algo == 'local':
        return min_conflicts(csp, max_steps=mc_steps, random_seed=seed)

    raise ValueError(
        f"Unknown algorithm '{algorithm}'. "
        "Choose from: backtrack, fc, mac, min_conflicts"
    )