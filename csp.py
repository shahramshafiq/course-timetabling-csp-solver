"""
csp.py  --  Core CSP Framework used by the timetabling problem.
"""

import copy
import random


# simple constraint class
class Constraint:
    """
    A constraint over some variables (its scope).
    check_func gets {var: value, ...} and returns True/False.
    """

    def __init__(self, scope, check_func, name="unnamed"):
        self.scope = list(scope)
        self.check_func = check_func
        self.name = name

    def is_satisfied(self, assignment):
        # if some variable in scope is not assigned yet, we treat it as ok
        for var in self.scope:
            if var not in assignment:
                return True

        vals = {}
        for v in self.scope:
            vals[v] = assignment[v]
        return self.check_func(vals)

    def is_violated(self, assignment):
        return not self.is_satisfied(assignment)

    def __repr__(self):
        return f"Constraint({self.name}, scope={self.scope})"


# main CSP class
class CSP:
    """
    Generic constraint satisfaction problem.
    Variables have domains, and constraints connect them.
    """

    def __init__(self):
        self.variables = []          # keeps variable order
        self.domains = {}            # var -> list of values
        self.constraints = []        # list of Constraint objects
        self.neighbors = {}          # var -> set of vars sharing any constraint
        self.constraint_checks = 0   # counter for performance

    # building the CSP
    def add_variable(self, var, domain):
        """add a new variable with its domain"""
        if var in self.domains:
            raise ValueError(f"Variable '{var}' already exists.")
        self.variables.append(var)
        self.domains[var] = list(domain)
        self.neighbors[var] = set()

    def add_constraint(self, constraint):
        """add a new constraint and update neighbors"""
        self.constraints.append(constraint)
        for v in constraint.scope:
            for u in constraint.scope:
                if u != v:
                    self.neighbors[v].add(u)

    # basic queries
    def get_constraints_for(self, var):
        """all constraints that mention var"""
        result = []
        for c in self.constraints:
            if var in c.scope:
                result.append(c)
        return result

    def get_binary_constraints(self, var1, var2):
        """constraints that involve both var1 and var2"""
        result = []
        for c in self.constraints:
            if var1 in c.scope and var2 in c.scope:
                result.append(c)
        return result

    def get_unassigned(self, assignment):
        """vars that are not in the assignment yet"""
        result = []
        for v in self.variables:
            if v not in assignment:
                result.append(v)
        return result

    def is_complete(self, assignment):
        """true if all variables are assigned"""
        return len(assignment) == len(self.variables)

    def domain_size(self, var):
        return len(self.domains[var])

    # consistency checking
    def is_consistent(self, var, value, assignment):
        """
        check if setting var=value breaks any constraints
        with already-assigned variables
        """
        test = {}
        for k, v in assignment.items():
            test[k] = v
        test[var] = value

        cons = self.get_constraints_for(var)
        for c in cons:
            self.constraint_checks += 1
            if not c.is_satisfied(test):
                return False
        return True

    def count_conflicts(self, var, value, assignment):
        """
        number of future conflicts if we set var=value
        (used by LCV heuristic)
        """
        test = {}
        for k, v in assignment.items():
            test[k] = v
        test[var] = value
        conflicts = 0

        for nb in self.neighbors[var]:
            if nb in assignment:
                continue

            for nb_val in self.domains[nb]:
                test[nb] = nb_val
                cons = self.get_binary_constraints(var, nb)
                broken = False
                for c in cons:
                    self.constraint_checks += 1
                    if not c.is_satisfied(test):
                        conflicts += 1
                        broken = True
                        break
                if broken:
                    continue

                # clean up for next value
            if nb in test:
                del test[nb]

        return conflicts

    # domain snapshots (for undoing pruning)
    def copy_domains(self):
        """shallow copy of domains dict"""
        snap = {}
        for v, d in self.domains.items():
            snap[v] = list(d)
        return snap

    def restore_domains(self, snapshot):
        """restore domains from snapshot"""
        new_domains = {}
        for v, d in snapshot.items():
            new_domains[v] = list(d)
        self.domains = new_domains

    # forward checking helper
    def prune_domain(self, var, value):
        """remove one value from var's domain"""
        if value in self.domains[var]:
            self.domains[var].remove(value)
        return len(self.domains[var]) > 0

    def has_empty_domain(self):
        """true if any domain is empty"""
        for d in self.domains.values():
            if len(d) == 0:
                return True
        return False

    # arc helpers (for AC-3 / MAC)
    def get_all_arcs(self):
        """all directed arcs (Xi, Xj) for every binary constraint"""
        arcs = []
        for c in self.constraints:
            if len(c.scope) == 2:
                xi = c.scope[0]
                xj = c.scope[1]
                arcs.append((xi, xj))
                arcs.append((xj, xi))
        return arcs

    def get_arcs_to(self, var, assigned_var):
        """
        arcs (nb, var) for every neighbour of var
        (except assigned_var)
        """
        arcs = []
        for nb in self.neighbors[var]:
            if nb != assigned_var:
                arcs.append((nb, var))
        return arcs

    # local search helpers
    def conflicts_count(self, var, value, assignment):
        """
        how many constraints are violated if var=value
        given a complete assignment
        """
        test = {}
        for k, v in assignment.items():
            test[k] = v
        test[var] = value
        count = 0
        cons = self.get_constraints_for(var)
        for c in cons:
            self.constraint_checks += 1
            if not c.is_satisfied(test):
                count += 1
        return count

    def get_conflicted_vars(self, assignment):
        """variables that violate at least one constraint"""
        conflicted = []
        for var in self.variables:
            cons = self.get_constraints_for(var)
            for c in cons:
                self.constraint_checks += 1
                if not c.is_satisfied(assignment):
                    if var not in conflicted:
                        conflicted.append(var)
                    break
        return conflicted

    def total_violations(self, assignment):
        """total number of violated constraints"""
        violations = 0
        seen = set()
        for c in self.constraints:
            cid = id(c)
            if cid in seen:
                continue
            seen.add(cid)
            self.constraint_checks += 1
            if not c.is_satisfied(assignment):
                violations += 1
        return violations

    # soft scoring (simple bonus points)
    def soft_score(self, assignment, instructor_prefs, room_prefs):
        """
        basic soft score: instructor time prefs + room prefs
        """
        score = 0
        for var, val in assignment.items():
            slot_id, room_id = val

            if var in instructor_prefs:
                pref_slots = instructor_prefs[var]
                if slot_id in pref_slots:
                    score += 5

            if var in room_prefs:
                pref_rooms = room_prefs[var]
                if room_id in pref_rooms:
                    score += 2

        return score

    # stats
    def reset_stats(self):
        """reset constraint check counter"""
        self.constraint_checks = 0

    def __repr__(self):
        return (
            f"CSP(variables={len(self.variables)}, "
            f"constraints={len(self.constraints)}, "
            f"constraint_checks={self.constraint_checks})"
        )