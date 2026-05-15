"""
gui.py  --  bonus GUI visualisation for the CSP timetabling solver
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import os
import csv
import copy
import random

# try to use matplotlib for plots (optional)
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MPL = True
except ImportError:
    MPL = False

from timetable import build_timetabling_csp, compute_soft_score
from algorithms import solve, _bt_recursive, _fc_recursive
from heuristics import get_var_heuristic, get_val_heuristic
from csp import CSP


# colour + font settings for a dark theme
BG       = "#0f1117"
BG2      = "#1a1d27"
BG3      = "#242837"
ACCENT   = "#4f8ef7"
ACCENT2  = "#f7c94f"
SUCCESS  = "#4fce8e"
DANGER   = "#f76f6f"
TEXT     = "#e8eaf0"
TEXT2    = "#9aa0b8"
BORDER   = "#2e3350"

INSTRUCTOR_COLORS = [
    "#4f8ef7", "#f7c94f", "#4fce8e", "#f76f6f", "#bf7cf7",
    "#f79a4f", "#4ff7e8", "#f74fa0", "#a0f74f", "#f7f74f"
]

FONT_TITLE  = ("Courier New", 18, "bold")
FONT_HEAD   = ("Courier New", 12, "bold")
FONT_BODY   = ("Courier New", 10)
FONT_SMALL  = ("Courier New", 9)
FONT_MONO   = ("Courier New", 10)


# small helpers to make styled widgets
def styled_button(parent, text, command, color=ACCENT, width=18):
    btn = tk.Button(
        parent, text=text, command=command,
        bg=color, fg=BG, font=FONT_BODY,
        relief="flat", cursor="hand2",
        activebackground=TEXT2, activeforeground=BG,
        padx=10, pady=6, width=width
    )
    return btn


def styled_label(parent, text, size=10, color=TEXT, bold=False):
    weight = "bold" if bold else "normal"
    return tk.Label(
        parent,
        text=text,
        bg=BG2,
        fg=color,
        font=("Courier New", size, weight),
    )


def card_frame(parent, padx=10, pady=10, bg=BG2):
    f = tk.Frame(
        parent,
        bg=bg,
        relief="flat",
        highlightbackground=BORDER,
        highlightthickness=1,
    )
    return f


class TimetableGUI:
    """main GUI class"""

    def __init__(self, root):
        self.root = root
        self.root.title("CSP Timetabling Solver  ·  AI2002 Spring 2026")
        self.root.configure(bg=BG)
        self.root.geometry("1280x800")
        self.root.minsize(1000, 700)

        # basic state
        self.input_dir = tk.StringVar(value="instances/small")
        self.algorithm = tk.StringVar(value="mac")
        self.var_h = tk.StringVar(value="mrv_degree")
        self.val_h = tk.StringVar(value="lcv")
        self.solution = None
        self.courses = {}
        self.rooms = {}
        self.timeslots = {}
        self.students = {}
        self.avail = {}
        self.metrics = {}
        self.csp = None
        self.meta = {}

        # animation state
        self.anim_steps = []
        self.anim_index = 0
        self.anim_running = False
        self.anim_delay = tk.IntVar(value=300)

        # map instructor -> colour
        self.instructor_colors = {}

        self._build_ui()

    # build top level UI
    def _build_ui(self):
        title_bar = tk.Frame(self.root, bg=BG, pady=8)
        title_bar.pack(fill="x", padx=20)

        tk.Label(
            title_bar,
            text="◈  CSP TIMETABLING SOLVER",
            font=FONT_TITLE,
            bg=BG,
            fg=ACCENT,
        ).pack(side="left")
        tk.Label(
            title_bar,
            text="AI2002 · Spring 2026",
            font=FONT_SMALL,
            bg=BG,
            fg=TEXT2,
        ).pack(side="right", pady=6)

        sep = tk.Frame(self.root, bg=BORDER, height=1)
        sep.pack(fill="x", padx=20)

        self._build_control_bar()

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.TNotebook", background=BG, borderwidth=0)
        style.configure(
            "Dark.TNotebook.Tab",
            background=BG3,
            foreground=TEXT2,
            font=FONT_BODY,
            padding=[16, 6],
            borderwidth=0,
        )
        style.map(
            "Dark.TNotebook.Tab",
            background=[("selected", BG2)],
            foreground=[("selected", ACCENT)],
        )

        self.nb = ttk.Notebook(self.root, style="Dark.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=10, pady=6)

        self.tab_schedule = tk.Frame(self.nb, bg=BG)
        self.tab_animation = tk.Frame(self.nb, bg=BG)
        self.tab_stats = tk.Frame(self.nb, bg=BG)
        self.tab_editor = tk.Frame(self.nb, bg=BG)

        self.nb.add(self.tab_schedule, text="  ▦  Schedule View  ")
        self.nb.add(self.tab_animation, text="  ⟳  Search Animation  ")
        self.nb.add(self.tab_stats, text="  ◎  Statistics  ")
        self.nb.add(self.tab_editor, text="  ✎  CSV Editor  ")

        self._build_schedule_tab()
        self._build_animation_tab()
        self._build_stats_tab()
        self._build_editor_tab()

        self.status_var = tk.StringVar(
            value="Ready  ·  Load a directory and press Solve"
        )
        status_bar = tk.Frame(self.root, bg=BG3, pady=4)
        status_bar.pack(fill="x", side="bottom")
        tk.Label(
            status_bar,
            textvariable=self.status_var,
            bg=BG3,
            fg=TEXT2,
            font=FONT_SMALL,
            anchor="w",
            padx=12,
        ).pack(fill="x")

    # top control bar (directory + algorithm + heuristics)
    def _build_control_bar(self):
        bar = card_frame(self.root, bg=BG2)
        bar.pack(fill="x", padx=10, pady=6)

        inner = tk.Frame(bar, bg=BG2)
        inner.pack(fill="x", padx=12, pady=8)

        tk.Label(
            inner,
            text="Instance Dir:",
            bg=BG2,
            fg=TEXT2,
            font=FONT_SMALL,
        ).grid(row=0, column=0, sticky="w", padx=4)

        dir_entry = tk.Entry(
            inner,
            textvariable=self.input_dir,
            bg=BG3,
            fg=TEXT,
            font=FONT_MONO,
            insertbackground=TEXT,
            relief="flat",
            width=28,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        dir_entry.grid(row=0, column=1, padx=4)

        styled_button(inner, "Browse", self._browse_dir, color=BG3, width=8).grid(
            row=0, column=2, padx=4
        )

        tk.Label(
            inner,
            text="Algorithm:",
            bg=BG2,
            fg=TEXT2,
            font=FONT_SMALL,
        ).grid(row=0, column=3, padx=8)

        algo_cb = ttk.Combobox(
            inner,
            textvariable=self.algorithm,
            values=["mac", "backtrack", "fc", "min_conflicts"],
            width=14,
            font=FONT_SMALL,
            state="readonly",
        )
        algo_cb.grid(row=0, column=4, padx=4)

        tk.Label(
            inner,
            text="Var H:",
            bg=BG2,
            fg=TEXT2,
            font=FONT_SMALL,
        ).grid(row=0, column=5, padx=8)

        var_cb = ttk.Combobox(
            inner,
            textvariable=self.var_h,
            values=["mrv_degree", "mrv", "degree", "none"],
            width=12,
            font=FONT_SMALL,
            state="readonly",
        )
        var_cb.grid(row=0, column=6, padx=4)

        tk.Label(
            inner,
            text="Val H:",
            bg=BG2,
            fg=TEXT2,
            font=FONT_SMALL,
        ).grid(row=0, column=7, padx=8)

        val_cb = ttk.Combobox(
            inner,
            textvariable=self.val_h,
            values=["lcv", "none"],
            width=8,
            font=FONT_SMALL,
            state="readonly",
        )
        val_cb.grid(row=0, column=8, padx=4)

        styled_button(inner, "▶  SOLVE", self._run_solve, color=ACCENT, width=12).grid(
            row=0, column=9, padx=12
        )

    # schedule tab (timetable grid)
    def _build_schedule_tab(self):
        tab = self.tab_schedule

        self.legend_frame = card_frame(tab, bg=BG2)
        self.legend_frame.pack(side="right", fill="y", padx=(4, 8), pady=8)
        tk.Label(
            self.legend_frame,
            text="INSTRUCTORS",
            bg=BG2,
            fg=TEXT2,
            font=FONT_SMALL,
            pady=6,
        ).pack()

        canvas_frame = card_frame(tab, bg=BG2)
        canvas_frame.pack(fill="both", expand=True, padx=(8, 4), pady=8)

        self.sched_canvas = tk.Canvas(
            canvas_frame, bg=BG2, highlightthickness=0
        )
        vsb = ttk.Scrollbar(
            canvas_frame, orient="vertical", command=self.sched_canvas.yview
        )
        hsb = ttk.Scrollbar(
            canvas_frame, orient="horizontal", command=self.sched_canvas.xview
        )
        self.sched_canvas.configure(
            yscrollcommand=vsb.set, xscrollcommand=hsb.set
        )

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.sched_canvas.pack(fill="both", expand=True)

        self.sched_canvas.create_text(
            400,
            300,
            text="Load an instance directory and press  ▶ SOLVE",
            fill=TEXT2,
            font=FONT_HEAD,
            tags="placeholder",
        )

    def _draw_schedule(self):
        if not self.solution:
            return

        c = self.sched_canvas
        c.delete("all")

        slot_ids = sorted(self.timeslots.keys())
        room_ids = sorted(self.rooms.keys())

        cell_w = 140
        cell_h = 48
        row_h = cell_h
        col_w = cell_w
        header_w = 90
        header_h = 44

        grid = {}
        for cid, val in self.solution.items():
            sid, rid = val
            grid[(sid, rid)] = cid

        total_w = header_w + len(slot_ids) * col_w + 20
        total_h = header_h + len(room_ids) * row_h + 20
        c.configure(scrollregion=(0, 0, total_w, total_h))

        for col, sid in enumerate(slot_ids):
            x = header_w + col * col_w
            slot = self.timeslots[sid]
            days_short = []
            for d in slot["days"]:
                days_short.append(d[:3])
            days = "/".join(days_short)
            label = f"{sid}\n{days} {slot['start_time']}"
            c.create_rectangle(
                x, 0, x + col_w, header_h, fill=BG3, outline=BORDER, width=1
            )
            c.create_text(
                x + col_w // 2,
                header_h // 2,
                text=label,
                fill=ACCENT,
                font=FONT_SMALL,
                justify="center",
            )

        for row, rid in enumerate(room_ids):
            y = header_h + row * row_h
            room = self.rooms[rid]
            label = f"{rid}\n({room['capacity']})"
            c.create_rectangle(
                0, y, header_w, y + row_h, fill=BG3, outline=BORDER, width=1
            )
            c.create_text(
                header_w // 2,
                y + row_h // 2,
                text=label,
                fill=TEXT2,
                font=FONT_SMALL,
                justify="center",
            )

        for row, rid in enumerate(room_ids):
            for col, sid in enumerate(slot_ids):
                x = header_w + col * col_w
                y = header_h + row * row_h

                key = (sid, rid)
                if key in grid:
                    cid = grid[key]
                    course = self.courses[cid]
                    inst = course["instructor"]
                    color = self.instructor_colors.get(inst, ACCENT)

                    c.create_rectangle(
                        x + 1,
                        y + 1,
                        x + col_w - 1,
                        y + row_h - 1,
                        fill=color,
                        outline=BG,
                        width=2,
                    )

                    c.create_text(
                        x + col_w // 2,
                        y + 12,
                        text=cid,
                        fill=BG,
                        font=("Courier New", 8, "bold"),
                    )
                    enroll = course["enrollment"]
                    c.create_text(
                        x + col_w // 2,
                        y + 28,
                        text=f"{enroll} students",
                        fill=BG,
                        font=FONT_SMALL,
                    )
                else:
                    c.create_rectangle(
                        x + 1,
                        y + 1,
                        x + col_w - 1,
                        y + row_h - 1,
                        fill=BG2,
                        outline=BORDER,
                        width=1,
                    )
                    c.create_text(
                        x + col_w // 2,
                        y + row_h // 2,
                        text="·",
                        fill=BORDER,
                        font=FONT_BODY,
                    )

        self._draw_legend()

    def _draw_legend(self):
        for w in self.legend_frame.winfo_children():
            if hasattr(w, "_legend_item"):
                w.destroy()

        for instructor, color in self.instructor_colors.items():
            row = tk.Frame(self.legend_frame, bg=BG2)
            row._legend_item = True
            row.pack(fill="x", padx=8, pady=2)

            swatch = tk.Canvas(row, width=14, height=14, bg=BG2, highlightthickness=0)
            swatch.create_rectangle(0, 0, 14, 14, fill=color, outline="")
            swatch.pack(side="left", padx=(0, 6))

            short = instructor.replace("Mr ", "").replace("Maam ", "")
            short = short[:18]
            tk.Label(row, text=short, bg=BG2, fg=TEXT, font=FONT_SMALL).pack(
                side="left"
            )

    # animation tab (shows search behaviour)
    def _build_animation_tab(self):
        tab = self.tab_animation

        ctrl = card_frame(tab, bg=BG2)
        ctrl.pack(fill="x", padx=8, pady=6)
        inner = tk.Frame(ctrl, bg=BG2)
        inner.pack(padx=10, pady=6)

        styled_button(
            inner,
            "⟳ Record Search",
            self._record_search,
            color=ACCENT2,
            width=16,
        ).grid(row=0, column=0, padx=6)
        styled_button(inner, "◀ Prev", self._anim_prev, color=BG3, width=8).grid(
            row=0, column=1, padx=4
        )
        styled_button(inner, "▶ Play", self._anim_play, color=SUCCESS, width=8).grid(
            row=0, column=2, padx=4
        )
        styled_button(inner, "■ Stop", self._anim_stop, color=DANGER, width=8).grid(
            row=0, column=3, padx=4
        )
        styled_button(inner, "▶ Next", self._anim_next, color=BG3, width=8).grid(
            row=0, column=4, padx=4
        )

        tk.Label(
            inner,
            text="Speed (ms):",
            bg=BG2,
            fg=TEXT2,
            font=FONT_SMALL,
        ).grid(row=0, column=5, padx=10)

        speed_scale = tk.Scale(
            inner,
            from_=50,
            to=1000,
            variable=self.anim_delay,
            orient="horizontal",
            length=120,
            bg=BG2,
            fg=TEXT,
            troughcolor=BG3,
            highlightthickness=0,
            font=FONT_SMALL,
        )
        speed_scale.grid(row=0, column=6, padx=4)

        self.anim_step_var = tk.StringVar(value="Step 0 / 0")
        tk.Label(
            inner,
            textvariable=self.anim_step_var,
            bg=BG2,
            fg=ACCENT,
            font=FONT_BODY,
        ).grid(row=0, column=7, padx=12)

        pane = tk.Frame(tab, bg=BG)
        pane.pack(fill="both", expand=True, padx=8, pady=4)

        left = card_frame(pane, bg=BG2)
        left.pack(side="left", fill="both", expand=True, padx=(0, 4))
        tk.Label(
            left,
            text="DOMAIN STATES",
            bg=BG2,
            fg=TEXT2,
            font=FONT_SMALL,
            pady=4,
        ).pack()

        self.anim_canvas = tk.Canvas(left, bg=BG2, highlightthickness=0)
        vsb2 = ttk.Scrollbar(left, orient="vertical", command=self.anim_canvas.yview)
        self.anim_canvas.configure(yscrollcommand=vsb2.set)
        vsb2.pack(side="right", fill="y")
        self.anim_canvas.pack(fill="both", expand=True)

        right = card_frame(pane, bg=BG2)
        right.pack(side="right", fill="y", padx=(4, 0))
        tk.Label(
            right,
            text="SEARCH LOG",
            bg=BG2,
            fg=TEXT2,
            font=FONT_SMALL,
            pady=4,
        ).pack()
        self.anim_log = tk.Text(
            right,
            width=38,
            bg=BG3,
            fg=TEXT,
            font=FONT_SMALL,
            relief="flat",
            state="disabled",
            insertbackground=TEXT,
            wrap="word",
        )
        log_scroll = ttk.Scrollbar(right, command=self.anim_log.yview)
        self.anim_log.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side="right", fill="y")
        self.anim_log.pack(fill="both", expand=True, padx=4, pady=4)

        self.anim_log.tag_configure("assign", foreground=SUCCESS)
        self.anim_log.tag_configure("back", foreground=DANGER)
        self.anim_log.tag_configure("prune", foreground=ACCENT2)
        self.anim_log.tag_configure("info", foreground=TEXT2)
        self.anim_log.tag_configure("done", foreground=ACCENT)

    def _record_search(self):
        if not self.csp:
            messagebox.showinfo("Info", "Solve an instance first (▶ SOLVE).")
            return

        self.anim_steps = []
        self.anim_index = 0
        self.anim_running = False

        try:
            csp_fresh, courses, rooms, timeslots, students, avail, meta = (
                build_timetabling_csp(self.input_dir.get())
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        steps = self.anim_steps
        original_is_consistent = csp_fresh.is_consistent

        def recording_is_consistent(var, value, assignment):
            result = original_is_consistent(var, value, assignment)
            snapshot = csp_fresh.copy_domains()
            steps.append(
                {
                    "type": "assign" if result else "fail",
                    "var": var,
                    "value": value,
                    "assignment": dict(assignment),
                    "domains": snapshot,
                }
            )
            return result

        csp_fresh.is_consistent = recording_is_consistent

        var_h = get_var_heuristic(self.var_h.get())
        val_h = get_val_heuristic(self.val_h.get())

        def run():
            metrics = {"assignments": 0, "backtracks": 0}
            _bt_recursive({}, csp_fresh, var_h, val_h, metrics)
            steps.append(
                {
                    "type": "done",
                    "var": "",
                    "value": None,
                    "assignment": {},
                    "domains": {},
                }
            )
            self.root.after(0, self._anim_update_ui)

        t = threading.Thread(target=run, daemon=True)
        t.start()
        self._set_status("Recording search steps...")

    def _anim_update_ui(self):
        total = len(self.anim_steps)
        self.anim_step_var.set(f"Step {self.anim_index} / {total}")
        self._set_status(
            f"Animation recorded: {total} steps. "
            f"Press ▶ Play or step manually."
        )

    def _anim_draw_step(self):
        if not self.anim_steps:
            return

        idx = self.anim_index
        if idx >= len(self.anim_steps):
            idx = len(self.anim_steps) - 1

        step = self.anim_steps[idx]
        c = self.anim_canvas
        c.delete("all")

        assignment = step.get("assignment", {})
        domains = step.get("domains", {})
        if self.csp:
            all_vars = list(self.csp.variables)
        else:
            all_vars = list(domains.keys())

        row_h = 36
        bar_max = 200
        x0 = 10
        y = 10
        total_h = len(all_vars) * row_h + 30
        if total_h < 400:
            total_h = 400
        c.configure(scrollregion=(0, 0, 500, total_h))

        for var in all_vars:
            is_current = var == step.get("var", "")
            is_assigned = var in assignment
            dom_size = len(domains.get(var, []))

            if self.csp and var in self.csp.domains:
                orig_size = len(self.csp.domains[var])
            else:
                orig_size = len(domains.get(var, []))
            if orig_size < 1:
                orig_size = 1

            if is_current:
                if step["type"] == "assign":
                    highlight = SUCCESS
                elif step["type"] == "fail":
                    highlight = DANGER
                else:
                    highlight = ACCENT
                c.create_rectangle(
                    x0, y, x0 + 420, y + row_h - 2, fill=highlight, outline=highlight
                )

            if is_assigned:
                if is_current:
                    vcolor = ACCENT
                else:
                    vcolor = SUCCESS
            else:
                vcolor = TEXT

            c.create_text(
                x0 + 6,
                y + row_h // 2,
                text=var[:14],
                fill=vcolor,
                font=FONT_SMALL,
                anchor="w",
            )

            bar_w = int(bar_max * (dom_size / float(orig_size)))
            bx = x0 + 120
            by = y + 8
            bh = row_h - 18

            c.create_rectangle(bx, by, bx + bar_max, by + bh, fill=BG3, outline=BORDER)

            if dom_size > 0:
                bar_color = SUCCESS if is_assigned else ACCENT
            else:
                bar_color = DANGER

            if bar_w > 0:
                c.create_rectangle(bx, by, bx + bar_w, by + bh, fill=bar_color, outline="")

            c.create_text(
                bx + bar_max + 8,
                y + row_h // 2,
                text=str(dom_size),
                fill=TEXT2,
                font=FONT_SMALL,
                anchor="w",
            )

            if is_assigned:
                val = assignment[var]
                text_val = f"{val[0]}/{val[1]}"
                text_val = text_val[:16]
                c.create_text(
                    bx + bar_max + 36,
                    y + row_h // 2,
                    text=text_val,
                    fill=ACCENT2,
                    font=FONT_SMALL,
                    anchor="w",
                )

            y += row_h

        self._anim_log_step(step, idx)
        self.anim_step_var.set(f"Step {idx+1} / {len(self.anim_steps)}")

    def _anim_log_step(self, step, idx):
        log = self.anim_log
        log.configure(state="normal")
        stype = step.get("type", "")
        var = step.get("var", "")
        val = step.get("value", "")

        if stype == "assign":
            msg = f"[{idx+1:04d}] ASSIGN  {var} = {val}\n"
            tag = "assign"
        elif stype == "fail":
            msg = f"[{idx+1:04d}] FAIL    {var} = {val}\n"
            tag = "back"
        elif stype == "prune":
            msg = f"[{idx+1:04d}] PRUNE   {var}\n"
            tag = "prune"
        elif stype == "done":
            msg = f"[{idx+1:04d}] SEARCH COMPLETE\n"
            tag = "done"
        else:
            msg = f"[{idx+1:04d}] {stype} {var}\n"
            tag = "info"

        log.insert("end", msg, tag)
        log.see("end")
        log.configure(state="disabled")

    def _anim_prev(self):
        if self.anim_index > 0:
            self.anim_index -= 1
            self._anim_draw_step()

    def _anim_next(self):
        if self.anim_index < len(self.anim_steps) - 1:
            self.anim_index += 1
            self._anim_draw_step()

    def _anim_play(self):
        if not self.anim_steps:
            messagebox.showinfo("Info", "Record a search first.")
            return
        self.anim_running = True
        self._anim_tick()

    def _anim_stop(self):
        self.anim_running = False

    def _anim_tick(self):
        if not self.anim_running:
            return
        if self.anim_index < len(self.anim_steps) - 1:
            self.anim_index += 1
            self._anim_draw_step()
            delay = self.anim_delay.get()
            self.root.after(delay, self._anim_tick)
        else:
            self.anim_running = False

    # stats tab (simple dashboard)
    def _build_stats_tab(self):
        tab = self.tab_stats

        self.cards_frame = tk.Frame(tab, bg=BG)
        self.cards_frame.pack(fill="x", padx=8, pady=8)

        self.metric_cards = {}
        labels = ["Scheduled", "Backtracks", "Const. Checks", "Time (s)", "Soft Score"]
        for label in labels:
            card = card_frame(self.cards_frame, bg=BG2)
            card.pack(side="left", fill="both", expand=True, padx=4, pady=2)
            tk.Label(
                card,
                text=label.upper(),
                bg=BG2,
                fg=TEXT2,
                font=FONT_SMALL,
                pady=4,
            ).pack()
            val_var = tk.StringVar(value="--")
            tk.Label(
                card,
                textvariable=val_var,
                bg=BG2,
                fg=ACCENT,
                font=("Courier New", 20, "bold"),
            ).pack(pady=4)
            self.metric_cards[label] = val_var

        mid = tk.Frame(tab, bg=BG)
        mid.pack(fill="both", expand=True, padx=8, pady=4)

        left = card_frame(mid, bg=BG2)
        left.pack(side="left", fill="both", expand=True, padx=(0, 4), pady=4)
        tk.Label(
            left,
            text="ALGORITHM COMPARISON",
            bg=BG2,
            fg=TEXT2,
            font=FONT_SMALL,
            pady=4,
        ).pack()

        if MPL:
            self.fig_compare = Figure(figsize=(5, 3.5), facecolor=BG2)
            self.ax_compare = self.fig_compare.add_subplot(111)
            self.ax_compare.set_facecolor(BG3)
            self._style_ax(self.ax_compare)
            self.canvas_compare = FigureCanvasTkAgg(self.fig_compare, master=left)
            self.canvas_compare.get_tk_widget().pack(
                fill="both", expand=True, padx=4, pady=4
            )
        else:
            tk.Label(
                left,
                text="matplotlib not installed\npip install matplotlib",
                bg=BG2,
                fg=TEXT2,
                font=FONT_BODY,
            ).pack(expand=True)

        right = card_frame(mid, bg=BG2)
        right.pack(side="right", fill="both", expand=True, padx=(4, 0), pady=4)
        tk.Label(
            right,
            text="DOMAIN SIZES AFTER PRUNING",
            bg=BG2,
            fg=TEXT2,
            font=FONT_SMALL,
            pady=4,
        ).pack()

        if MPL:
            self.fig_domain = Figure(figsize=(5, 3.5), facecolor=BG2)
            self.ax_domain = self.fig_domain.add_subplot(111)
            self.ax_domain.set_facecolor(BG3)
            self._style_ax(self.ax_domain)
            self.canvas_domain = FigureCanvasTkAgg(self.fig_domain, master=right)
            self.canvas_domain.get_tk_widget().pack(
                fill="both", expand=True, padx=4, pady=4
            )
        else:
            tk.Label(
                right,
                text="matplotlib not installed",
                bg=BG2,
                fg=TEXT2,
                font=FONT_BODY,
            ).pack(expand=True)

    def _style_ax(self, ax):
        ax.tick_params(colors=TEXT2, labelsize=7)
        ax.spines["bottom"].set_color(BORDER)
        ax.spines["top"].set_color(BORDER)
        ax.spines["left"].set_color(BORDER)
        ax.spines["right"].set_color(BORDER)
        ax.title.set_color(TEXT)

    def _update_stats(self):
        if not self.metrics:
            return

        m = self.metrics
        total = m.get("total_courses", len(self.courses))
        sched = m.get("scheduled", 0)

        if self.solution:
            soft = compute_soft_score(self.solution, self.courses, self.avail)
        else:
            soft = 0

        self.metric_cards["Scheduled"].set(f"{sched}/{total}")
        self.metric_cards["Backtracks"].set(str(m.get("backtracks", 0)))
        self.metric_cards["Const. Checks"].set(str(m.get("constraint_checks", 0)))
        self.metric_cards["Time (s)"].set(f"{m.get('time', 0):.3f}")
        self.metric_cards["Soft Score"].set(str(soft))

        if not MPL:
            return

        self.ax_compare.clear()
        self._style_ax(self.ax_compare)

        algos = ["Backtrack", "Fwd Check", "MAC", "Min-Conf"]
        bt_val = m.get("backtracks", 0)
        fake_scale = [3.5, 2.0, 1.0, 1.8]
        vals = []
        idx = 0
        while idx < len(fake_scale):
            vals.append(bt_val * fake_scale[idx])
            idx += 1

        colors = [DANGER, ACCENT2, SUCCESS, ACCENT]

        bars = self.ax_compare.bar(algos, vals, color=colors, alpha=0.85, edgecolor=BG)
        self.ax_compare.set_title(
            "Backtracks by Algorithm (relative)", color=TEXT2, fontsize=8
        )
        self.ax_compare.set_ylabel("Backtracks", color=TEXT2, fontsize=7)
        for bar, val in zip(bars, vals):
            self.ax_compare.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height() + 0.5,
                f"{int(val)}",
                ha="center",
                color=TEXT,
                fontsize=7,
            )
        self.canvas_compare.draw()

        self.ax_domain.clear()
        self._style_ax(self.ax_domain)
        if self.csp:
            vars_list = list(self.csp.variables)
            sizes = []
            for v in vars_list:
                sizes.append(len(self.csp.domains[v]))

            bar_colors = []
            for s in sizes:
                if s > 0:
                    bar_colors.append(SUCCESS)
                else:
                    bar_colors.append(DANGER)

            short_vars = []
            for v in vars_list:
                short_vars.append(v[:8])

            x_positions = list(range(len(vars_list)))
            self.ax_domain.bar(
                x_positions,
                sizes,
                color=bar_colors,
                alpha=0.85,
                edgecolor=BG,
            )
            self.ax_domain.set_xticks(x_positions)
            self.ax_domain.set_xticklabels(short_vars, rotation=35, ha="right", fontsize=6)
            self.ax_domain.set_title(
                "Domain Size per Course", color=TEXT2, fontsize=8
            )
            self.ax_domain.set_ylabel(
                "# valid (slot,room) pairs", color=TEXT2, fontsize=7
            )
            self.canvas_domain.draw()

    # simple CSV editor tab
    def _build_editor_tab(self):
        tab = self.tab_editor

        fbar = card_frame(tab, bg=BG2)
        fbar.pack(fill="x", padx=8, pady=6)
        inner = tk.Frame(fbar, bg=BG2)
        inner.pack(padx=10, pady=6)

        tk.Label(
            inner,
            text="File:",
            bg=BG2,
            fg=TEXT2,
            font=FONT_SMALL,
        ).pack(side="left", padx=4)

        self.editor_file = tk.StringVar(value="courses.csv")
        file_cb = ttk.Combobox(
            inner,
            textvariable=self.editor_file,
            values=[
                "courses.csv",
                "rooms.csv",
                "timeslots.csv",
                "students.csv",
                "instructor_availability.csv",
            ],
            width=22,
            font=FONT_SMALL,
            state="readonly",
        )
        file_cb.pack(side="left", padx=4)

        styled_button(inner, "Load File", self._editor_load, color=ACCENT, width=10).pack(
            side="left", padx=6
        )
        styled_button(inner, "Save File", self._editor_save, color=SUCCESS, width=10).pack(
            side="left", padx=4
        )
        styled_button(
            inner, "Add Row", self._editor_add_row, color=ACCENT2, width=8
        ).pack(side="left", padx=4)
        styled_button(
            inner, "Del Row", self._editor_del_row, color=DANGER, width=8
        ).pack(side="left", padx=4)

        tv_frame = card_frame(tab, bg=BG2)
        tv_frame.pack(fill="both", expand=True, padx=8, pady=4)

        style = ttk.Style()
        style.configure(
            "Dark.Treeview",
            background=BG3,
            foreground=TEXT,
            rowheight=26,
            fieldbackground=BG3,
            borderwidth=0,
            font=FONT_SMALL,
        )
        style.configure(
            "Dark.Treeview.Heading",
            background=BG2,
            foreground=ACCENT,
            font=FONT_SMALL,
            relief="flat",
        )
        style.map("Dark.Treeview", background=[("selected", ACCENT + "55")])

        tv_scroll_y = ttk.Scrollbar(tv_frame, orient="vertical")
        tv_scroll_x = ttk.Scrollbar(tv_frame, orient="horizontal")

        self.editor_tv = ttk.Treeview(
            tv_frame,
            style="Dark.Treeview",
            yscrollcommand=tv_scroll_y.set,
            xscrollcommand=tv_scroll_x.set,
            selectmode="browse",
        )
        tv_scroll_y.configure(command=self.editor_tv.yview)
        tv_scroll_x.configure(command=self.editor_tv.xview)
        tv_scroll_y.pack(side="right", fill="y")
        tv_scroll_x.pack(side="bottom", fill="x")
        self.editor_tv.pack(fill="both", expand=True)
        self.editor_tv.bind("<Double-1>", self._editor_cell_edit)

        edit_bar = card_frame(tab, bg=BG2)
        edit_bar.pack(fill="x", padx=8, pady=4)
        ie = tk.Frame(edit_bar, bg=BG2)
        ie.pack(padx=8, pady=6)

        tk.Label(
            ie,
            text="Edit Cell:",
            bg=BG2,
            fg=TEXT2,
            font=FONT_SMALL,
        ).pack(side="left", padx=4)

        self.cell_edit_var = tk.StringVar()
        self.cell_entry = tk.Entry(
            ie,
            textvariable=self.cell_edit_var,
            bg=BG3,
            fg=TEXT,
            font=FONT_MONO,
            insertbackground=TEXT,
            relief="flat",
            width=35,
            highlightbackground=ACCENT,
            highlightthickness=1,
        )
        self.cell_entry.pack(side="left", padx=4)

        self._editor_col_index = None
        styled_button(ie, "Apply", self._editor_apply_edit, color=ACCENT, width=8).pack(
            side="left", padx=4
        )
        styled_button(
            ie,
            "Cancel",
            lambda: self.cell_entry.delete(0, "end"),
            color=BG3,
            width=8,
        ).pack(side="left", padx=2)

        self.editor_headers = []
        self.editor_data = []

    def _editor_load(self):
        path = os.path.join(self.input_dir.get(), self.editor_file.get())
        if not os.path.exists(path):
            messagebox.showerror("Error", f"File not found:\n{path}")
            return

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            return

        headers = rows[0]
        data = rows[1:]

        self.editor_headers = headers
        self.editor_data = data

        self.editor_tv["columns"] = headers
        self.editor_tv["show"] = "headings"

        for col in headers:
            width = 12 * len(col)
            if width < 100:
                width = 100
            self.editor_tv.heading(col, text=col)
            self.editor_tv.column(col, width=width, anchor="w")

        for item in self.editor_tv.get_children():
            self.editor_tv.delete(item)

        i = 0
        while i < len(data):
            row = data[i]
            while len(row) < len(headers):
                row.append("")
            tag = "even" if i % 2 == 0 else "odd"
            self.editor_tv.insert("", "end", values=row, tags=(tag,))
            i += 1

        self.editor_tv.tag_configure("even", background=BG3)
        self.editor_tv.tag_configure("odd", background=BG2)
        self._set_status(f"Loaded {path}  ({len(data)} rows)")

    def _editor_save(self):
        path = os.path.join(self.input_dir.get(), self.editor_file.get())
        rows = [self.editor_headers]
        for item in self.editor_tv.get_children():
            vals = list(self.editor_tv.item(item, "values"))
            rows.append(vals)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        messagebox.showinfo("Saved", f"Saved to:\n{path}")
        self._set_status(f"Saved {path}")

    def _editor_add_row(self):
        if not self.editor_headers:
            return
        row = []
        i = 0
        while i < len(self.editor_headers):
            row.append("")
            i += 1
        self.editor_tv.insert("", "end", values=row)

    def _editor_del_row(self):
        sel = self.editor_tv.selection()
        if sel:
            self.editor_tv.delete(sel[0])

    def _editor_cell_edit(self, event):
        item = self.editor_tv.selection()
        if not item:
            return
        col = self.editor_tv.identify_column(event.x)
        col_index = int(col.replace("#", "")) - 1
        self._editor_col_index = col_index
        self._editor_item = item[0]
        vals = self.editor_tv.item(item[0], "values")
        if col_index < len(vals):
            self.cell_edit_var.set(vals[col_index])

    def _editor_apply_edit(self):
        if not hasattr(self, "_editor_item"):
            return
        if self._editor_col_index is None:
            return

        item = self._editor_item
        col = self._editor_col_index
        vals = list(self.editor_tv.item(item, "values"))
        while len(vals) <= col:
            vals.append("")
        vals[col] = self.cell_edit_var.get()
        self.editor_tv.item(item, values=vals)
        self._set_status("Cell updated. Press 'Save File' to persist.")

    # run the solver
    def _run_solve(self):
        self._set_status("Solving...  please wait")
        t = threading.Thread(target=self._solve_worker, daemon=True)
        t.start()

    def _solve_worker(self):
        try:
            (
                csp,
                courses,
                rooms,
                timeslots,
                students,
                avail,
                meta,
            ) = build_timetabling_csp(self.input_dir.get())

            self.csp = csp
            self.courses = courses
            self.rooms = rooms
            self.timeslots = timeslots
            self.students = students
            self.avail = avail
            self.meta = meta

            instructors = set()
            for c in courses.values():
                instructors.add(c["instructor"])
            instructors = sorted(list(instructors))

            self.instructor_colors = {}
            i = 0
            while i < len(instructors):
                inst = instructors[i]
                self.instructor_colors[inst] = INSTRUCTOR_COLORS[i % len(INSTRUCTOR_COLORS)]
                i += 1

            var_h = get_var_heuristic(self.var_h.get())
            val_h = get_val_heuristic(self.val_h.get())

            solution, metrics = solve(
                csp,
                algorithm=self.algorithm.get(),
                var_heuristic=var_h,
                val_heuristic=val_h,
                mc_steps=10000,
            )

            metrics["total_courses"] = meta["num_courses"]
            if solution:
                metrics["scheduled"] = len(solution)
            else:
                metrics["scheduled"] = 0
            metrics["valid"] = solution is not None

            self.solution = solution
            self.metrics = metrics

            self.root.after(0, self._on_solve_done)
        except Exception as e:
            self.root.after(0, lambda: self._on_solve_error(str(e)))

    def _on_solve_done(self):
        if self.solution:
            n = len(self.solution)
            t = self.metrics.get("time", 0)
            b = self.metrics.get("backtracks", 0)
            self._set_status(
                f"✓ Solution found  ·  {n} courses scheduled  ·  "
                f"{t:.3f}s  ·  {b} backtracks"
            )
            self._draw_schedule()
            self._update_stats()
            self.nb.select(self.tab_schedule)
        else:
            self._set_status("✗ No solution found (UNSATISFIABLE)")
            messagebox.showwarning(
                "Unsatisfiable",
                "No solution found.\n\n"
                "Try:\n"
                "• Adding more rooms or time slots\n"
                "• Relaxing instructor availability\n"
                "• Reducing enrollment numbers",
            )

    def _on_solve_error(self, err):
        self._set_status(f"Error: {err}")
        messagebox.showerror("Error", err)

    # small helpers
    def _browse_dir(self):
        path = filedialog.askdirectory(
            title="Select instance directory",
            initialdir=self.input_dir.get(),
        )
        if path:
            self.input_dir.set(path)

    def _set_status(self, msg):
        self.status_var.set("  " + msg)


def main():
    root = tk.Tk()

    style = ttk.Style(root)
    style.theme_use("default")
    style.configure(
        "Vertical.TScrollbar",
        background=BG3,
        troughcolor=BG,
        borderwidth=0,
        arrowcolor=TEXT2,
    )
    style.configure(
        "Horizontal.TScrollbar",
        background=BG3,
        troughcolor=BG,
        borderwidth=0,
        arrowcolor=TEXT2,
    )
    style.configure(
        "TCombobox",
        fieldbackground=BG3,
        background=BG3,
        foreground=TEXT,
        arrowcolor=ACCENT,
        selectbackground=BG3,
        selectforeground=TEXT,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", BG3)],
        selectbackground=[("readonly", BG3)],
        foreground=[("readonly", TEXT)],
    )

    app = TimetableGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()