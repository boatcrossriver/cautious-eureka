#!/usr/bin/env python3
"""
Visual Multithreading Demo for macOS
Run: python3 multithread_demo.py
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import random
import queue
from concurrent.futures import ThreadPoolExecutor

# Shared palette used by every demo tab so the UI stays consistent.
COLORS = {
    "bg": "#1e1e2e",
    "surface": "#313244",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "red": "#f38ba8",
    "green": "#a6e3a1",
    "yellow": "#f9e2af",
    "blue": "#89b4fa",
    "mauve": "#cba6f7",
    "teal": "#94e2d5",
    "peach": "#fab387",
    "pink": "#f5c2e7",
    "sky": "#89dceb",
    "lavender": "#b4befe",
}

THREAD_COLORS = [
    COLORS["red"], COLORS["green"], COLORS["blue"],
    COLORS["yellow"], COLORS["mauve"], COLORS["teal"],
    COLORS["peach"], COLORS["pink"], COLORS["sky"],
    COLORS["lavender"],
]


class ThreadRaceDemo(ttk.Frame):
    """Tab 1: Visual thread race - multiple threads update progress bars."""

    def __init__(self, parent):
        super().__init__(parent)
        self.running = False
        self.threads = []
        self.progress_values = {}
        self.bars = {}
        self.labels = {}
        self.num_threads = 6
        self._build_ui()

    def _build_ui(self):
        title = ttk.Label(self, text="🏁 Thread Race", font=("Helvetica", 18, "bold"))
        title.pack(pady=(10, 0))
        desc = ttk.Label(
            self,
            text="Each thread increments its progress bar at random speeds.\n"
                 "Watch them race - demonstrates concurrent execution.",
            font=("Helvetica", 11),
            justify="center",
        )
        desc.pack(pady=(0, 10))

        self.canvas = tk.Canvas(
            self, width=700, height=320, bg=COLORS["bg"], highlightthickness=0
        )
        self.canvas.pack(padx=20, pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        self.start_btn = ttk.Button(btn_frame, text="▶ Start Race", command=self.start_race)
        self.start_btn.pack(side="left", padx=5)
        self.reset_btn = ttk.Button(btn_frame, text="↺ Reset", command=self.reset)
        self.reset_btn.pack(side="left", padx=5)

        self.status_var = tk.StringVar(value="Ready - press Start")
        ttk.Label(self, textvariable=self.status_var, font=("Helvetica", 11)).pack()

        self._draw_tracks()

    def _draw_tracks(self):
        self.canvas.delete("all")
        bar_h = 30
        gap = 15
        x0, x1 = 120, 670
        y_start = 20
        for i in range(self.num_threads):
            y = y_start + i * (bar_h + gap)
            self.canvas.create_text(
                10, y + bar_h // 2, text=f"Thread-{i}",
                fill=THREAD_COLORS[i % len(THREAD_COLORS)],
                font=("Menlo", 12, "bold"), anchor="w",
            )
            self.canvas.create_rectangle(
                x0, y, x1, y + bar_h,
                fill=COLORS["surface"], outline=COLORS["subtext"], width=1,
            )
            # Store canvas ids so the polling loop can redraw the same items
            # instead of creating new shapes every frame.
            bar_id = self.canvas.create_rectangle(
                x0, y + 2, x0, y + bar_h - 2,
                fill=THREAD_COLORS[i % len(THREAD_COLORS)], outline="",
            )
            pct_id = self.canvas.create_text(
                x1 + 5, y + bar_h // 2, text="0%",
                fill=COLORS["text"], font=("Menlo", 10), anchor="w",
            )
            self.bars[i] = bar_id
            self.labels[i] = pct_id
            self.progress_values[i] = 0

    def start_race(self):
        if self.running:
            return
        self.reset()
        self.running = True
        self.start_btn.config(state="disabled")
        self.status_var.set("Racing...")
        for i in range(self.num_threads):
            # Worker threads update only plain Python state. Tk widgets stay on
            # the main thread and are refreshed by _poll_progress().
            t = threading.Thread(target=self._race_worker, args=(i,), daemon=True)
            self.threads.append(t)
            t.start()
        self._poll_progress()

    def _race_worker(self, tid):
        while self.running and self.progress_values[tid] < 100:
            time.sleep(random.uniform(0.01, 0.08))
            self.progress_values[tid] = min(
                100, self.progress_values[tid] + random.uniform(0.5, 3)
            )

    def _poll_progress(self):
        x0, x1 = 120, 670
        max_w = x1 - x0
        finished = []
        for i in range(self.num_threads):
            pct = self.progress_values[i]
            w = max_w * pct / 100
            coords = list(self.canvas.coords(self.bars[i]))
            coords[2] = x0 + w
            self.canvas.coords(self.bars[i], *coords)
            self.canvas.itemconfig(self.labels[i], text=f"{int(pct)}%")
            if pct >= 100:
                finished.append(i)

        if len(finished) >= self.num_threads:
            self.running = False
            winner = finished[0]
            self.status_var.set(f"🏆 Thread-{winner} wins!")
            self.start_btn.config(state="normal")
            return

        if finished and not hasattr(self, "_winner_announced"):
            self._winner_announced = True
            self.status_var.set(f"🏆 Thread-{finished[0]} finished first! Waiting for others...")

        # Tk's event loop drives animation. after() keeps UI updates on the
        # main thread and avoids touching widgets from worker threads.
        self.after(30, self._poll_progress)

    def reset(self):
        self.running = False
        self.threads.clear()
        if hasattr(self, "_winner_announced"):
            del self._winner_announced
        for i in range(self.num_threads):
            self.progress_values[i] = 0
        self._draw_tracks()
        self.start_btn.config(state="normal")
        self.status_var.set("Ready - press Start")


class ProducerConsumerDemo(ttk.Frame):
    """Tab 2: Animated producer-consumer with a bounded buffer."""

    def __init__(self, parent):
        super().__init__(parent)
        self.running = False
        self.buffer = queue.Queue(maxsize=10)
        self.buffer_items = []  # Mirror of queue contents for visualization only.
        self.lock = threading.Lock()
        self.produced = 0
        self.consumed = 0
        self._build_ui()

    def _build_ui(self):
        title = ttk.Label(self, text="📦 Producer-Consumer", font=("Helvetica", 18, "bold"))
        title.pack(pady=(10, 0))
        desc = ttk.Label(
            self,
            text="Producers add items to a bounded buffer (max 10).\n"
                 "Consumers remove them. Uses queue.Queue (thread-safe).",
            font=("Helvetica", 11), justify="center",
        )
        desc.pack(pady=(0, 10))

        self.canvas = tk.Canvas(
            self, width=700, height=280, bg=COLORS["bg"], highlightthickness=0
        )
        self.canvas.pack(padx=20, pady=5)

        ctrl = ttk.Frame(self)
        ctrl.pack(pady=5)
        self.start_btn = ttk.Button(ctrl, text="▶ Start", command=self.start)
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = ttk.Button(ctrl, text="⏹ Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        speed_frame = ttk.Frame(self)
        speed_frame.pack(pady=2)
        ttk.Label(speed_frame, text="Producers:").pack(side="left")
        self.prod_scale = ttk.Scale(speed_frame, from_=1, to=5, orient="horizontal", length=100)
        self.prod_scale.set(2)
        self.prod_scale.pack(side="left", padx=(2, 15))
        ttk.Label(speed_frame, text="Consumers:").pack(side="left")
        self.cons_scale = ttk.Scale(speed_frame, from_=1, to=5, orient="horizontal", length=100)
        self.cons_scale.set(2)
        self.cons_scale.pack(side="left", padx=2)

        self.stat_var = tk.StringVar(value="Produced: 0 | Consumed: 0 | Buffer: 0/10")
        ttk.Label(self, textvariable=self.stat_var, font=("Menlo", 11)).pack(pady=5)

    def _draw_buffer(self):
        self.canvas.delete("all")
        self.canvas.create_text(100, 30, text="PRODUCERS →", fill=COLORS["green"],
                                font=("Menlo", 14, "bold"))
        self.canvas.create_text(600, 30, text="→ CONSUMERS", fill=COLORS["red"],
                                font=("Menlo", 14, "bold"))
        self.canvas.create_text(350, 30, text="BUFFER", fill=COLORS["yellow"],
                                font=("Menlo", 14, "bold"))

        slot_w, slot_h = 50, 50
        x_start = 125
        y = 60
        for i in range(10):
            x = x_start + i * (slot_w + 5)
            fill = COLORS["surface"]
            outline = COLORS["subtext"]
            if i < len(self.buffer_items):
                fill = COLORS["peach"]
                outline = COLORS["yellow"]
            self.canvas.create_rectangle(
                x, y, x + slot_w, y + slot_h,
                fill=fill, outline=outline, width=2
            )
            if i < len(self.buffer_items):
                self.canvas.create_text(
                    x + slot_w // 2, y + slot_h // 2,
                    text=str(self.buffer_items[i]),
                    fill=COLORS["bg"], font=("Menlo", 11, "bold"),
                )

        n_prod = int(self.prod_scale.get())
        n_cons = int(self.cons_scale.get())
        for i in range(n_prod):
            yy = 140 + i * 40
            self.canvas.create_oval(30, yy, 60, yy + 30, fill=COLORS["green"], outline="")
            self.canvas.create_text(80, yy + 15, text=f"P-{i}", fill=COLORS["green"],
                                    font=("Menlo", 10))
        for i in range(n_cons):
            yy = 140 + i * 40
            self.canvas.create_oval(640, yy, 670, yy + 30, fill=COLORS["red"], outline="")
            self.canvas.create_text(620, yy + 15, text=f"C-{i}", fill=COLORS["red"],
                                    font=("Menlo", 10), anchor="e")

        self.stat_var.set(
            f"Produced: {self.produced} | Consumed: {self.consumed} | "
            f"Buffer: {len(self.buffer_items)}/10"
        )

    def start(self):
        self.running = True
        self.produced = 0
        self.consumed = 0
        self.buffer_items.clear()
        while not self.buffer.empty():
            try:
                self.buffer.get_nowait()
            except queue.Empty:
                break
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        n_prod = int(self.prod_scale.get())
        n_cons = int(self.cons_scale.get())
        for i in range(n_prod):
            threading.Thread(target=self._producer, args=(i,), daemon=True).start()
        for i in range(n_cons):
            threading.Thread(target=self._consumer, args=(i,), daemon=True).start()
        self._poll()

    def _producer(self, pid):
        while self.running:
            item = random.randint(1, 99)
            try:
                # Queue handles producer/consumer synchronization for the real
                # data path; the extra lock protects only the display mirror.
                self.buffer.put(item, timeout=0.5)
                with self.lock:
                    self.buffer_items.append(item)
                    self.produced += 1
            except queue.Full:
                pass
            time.sleep(random.uniform(0.3, 0.8))

    def _consumer(self, cid):
        while self.running:
            try:
                item = self.buffer.get(timeout=0.5)
                with self.lock:
                    if item in self.buffer_items:
                        self.buffer_items.remove(item)
                    self.consumed += 1
            except queue.Empty:
                pass
            time.sleep(random.uniform(0.4, 1.0))

    def _poll(self):
        if not self.running:
            return
        self._draw_buffer()
        self.after(100, self._poll)

    def stop(self):
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")


class RaceConditionDemo(ttk.Frame):
    """Tab 3: Shows race condition vs. proper locking."""

    def __init__(self, parent):
        super().__init__(parent)
        self.counter_no_lock = 0
        self.counter_with_lock = 0
        self.lock = threading.Lock()
        self._build_ui()

    def _build_ui(self):
        title = ttk.Label(self, text="⚠️ Race Condition Demo", font=("Helvetica", 18, "bold"))
        title.pack(pady=(10, 0))
        desc = ttk.Label(
            self,
            text="10 threads each increment a counter 100,000 times.\n"
                 "Expected result: 1,000,000. Without a lock, data races can corrupt totals.",
            font=("Helvetica", 11), justify="center",
        )
        desc.pack(pady=(0, 10))

        self.canvas = tk.Canvas(
            self, width=700, height=300, bg=COLORS["bg"], highlightthickness=0
        )
        self.canvas.pack(padx=20, pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        self.run_btn = ttk.Button(btn_frame, text="▶ Run Experiment", command=self.run_experiment)
        self.run_btn.pack()

        self.result_var = tk.StringVar(value="Press Run to begin experiment")
        ttk.Label(self, textvariable=self.result_var, font=("Menlo", 11)).pack(pady=5)

        self._draw_initial()

    def _draw_initial(self):
        self.canvas.delete("all")
        self.canvas.create_text(175, 30, text="WITHOUT Lock 🔓", fill=COLORS["red"],
                                font=("Helvetica", 16, "bold"))
        self.canvas.create_text(525, 30, text="WITH Lock 🔒", fill=COLORS["green"],
                                font=("Helvetica", 16, "bold"))
        self.canvas.create_line(350, 10, 350, 290, fill=COLORS["subtext"], dash=(4, 4))

        self.canvas.create_text(175, 70, text="Expected: 1,000,000",
                                fill=COLORS["subtext"], font=("Menlo", 11))
        self.canvas.create_text(525, 70, text="Expected: 1,000,000",
                                fill=COLORS["subtext"], font=("Menlo", 11))

        self._no_lock_text = self.canvas.create_text(
            175, 140, text="?", fill=COLORS["red"], font=("Menlo", 36, "bold")
        )
        self._with_lock_text = self.canvas.create_text(
            525, 140, text="?", fill=COLORS["green"], font=("Menlo", 36, "bold")
        )
        self._no_lock_verdict = self.canvas.create_text(
            175, 200, text="", fill=COLORS["yellow"], font=("Helvetica", 14, "bold")
        )
        self._with_lock_verdict = self.canvas.create_text(
            525, 200, text="", fill=COLORS["yellow"], font=("Helvetica", 14, "bold")
        )

    def run_experiment(self):
        self.run_btn.config(state="disabled")
        self.result_var.set("Running... (10 threads × 100,000 increments)")
        self._draw_initial()
        threading.Thread(target=self._experiment, daemon=True).start()

    def _experiment(self):
        num_threads = 10
        increments = 100_000

        # This deliberately performs a shared update without synchronization.
        # In CPython the exact outcome is timing-dependent, so it may still
        # occasionally land on the expected result.
        self.counter_no_lock = 0

        def inc_no_lock():
            for _ in range(increments):
                self.counter_no_lock += 1

        threads = [threading.Thread(target=inc_no_lock) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        result_no_lock = self.counter_no_lock

        self.counter_with_lock = 0

        def inc_with_lock():
            for _ in range(increments):
                with self.lock:
                    self.counter_with_lock += 1

        threads = [threading.Thread(target=inc_with_lock) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        result_with_lock = self.counter_with_lock

        expected = num_threads * increments
        self.after(0, self._show_results, result_no_lock, result_with_lock, expected)

    def _show_results(self, no_lock, with_lock, expected):
        self.canvas.itemconfig(self._no_lock_text, text=f"{no_lock:,}")
        self.canvas.itemconfig(self._with_lock_text, text=f"{with_lock:,}")

        if no_lock != expected:
            verdict_no = f"❌ WRONG! Off by {expected - no_lock:,}"
            self.canvas.itemconfig(self._no_lock_verdict, text=verdict_no, fill=COLORS["red"])
        else:
            self.canvas.itemconfig(self._no_lock_verdict, text="✓ Correct (got lucky!)",
                                   fill=COLORS["green"])

        if with_lock == expected:
            self.canvas.itemconfig(self._with_lock_verdict, text="✅ CORRECT!",
                                   fill=COLORS["green"])
        else:
            self.canvas.itemconfig(self._with_lock_verdict, text="❌ Error",
                                   fill=COLORS["red"])

        self.result_var.set("Done! Run again - the 'without lock' result can change each time.")
        self.run_btn.config(state="normal")


class ThreadPoolDemo(ttk.Frame):
    """Tab 4: ThreadPoolExecutor visual task processing."""

    def __init__(self, parent):
        super().__init__(parent)
        self.running = False
        self.tasks = []
        self.task_status = {}  # task id -> (status, worker_name, progress)
        self.lock = threading.Lock()
        self._build_ui()

    def _build_ui(self):
        title = ttk.Label(self, text="🏊 Thread Pool Executor", font=("Helvetica", 18, "bold"))
        title.pack(pady=(10, 0))
        desc = ttk.Label(
            self,
            text="Submit tasks to a pool of worker threads.\n"
                 "Uses concurrent.futures.ThreadPoolExecutor.",
            font=("Helvetica", 11), justify="center",
        )
        desc.pack(pady=(0, 10))

        self.canvas = tk.Canvas(
            self, width=700, height=320, bg=COLORS["bg"], highlightthickness=0
        )
        self.canvas.pack(padx=20, pady=5)

        ctrl = ttk.Frame(self)
        ctrl.pack(pady=5)
        ttk.Label(ctrl, text="Workers:").pack(side="left")
        self.worker_var = tk.IntVar(value=3)
        ttk.Spinbox(ctrl, from_=1, to=6, textvariable=self.worker_var, width=3).pack(
            side="left", padx=(2, 10)
        )
        self.run_btn = ttk.Button(ctrl, text="▶ Submit 12 Tasks", command=self.submit_tasks)
        self.run_btn.pack(side="left", padx=5)

        self.stat_var = tk.StringVar(value="Configure workers and submit tasks")
        ttk.Label(self, textvariable=self.stat_var, font=("Menlo", 11)).pack(pady=5)

    def submit_tasks(self):
        self.run_btn.config(state="disabled")
        self.task_status.clear()
        num_tasks = 12

        for i in range(num_tasks):
            self.task_status[i] = ("pending", None, 0)

        self.running = True
        # The pool runs off the Tk thread. The canvas still updates from _poll().
        threading.Thread(target=self._run_pool, args=(num_tasks,), daemon=True).start()
        self._poll()

    def _run_pool(self, num_tasks):
        workers = self.worker_var.get()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(self._task_work, i): i for i in range(num_tasks)}
            for f in futures:
                f.result()
        self.running = False

    def _task_work(self, task_id):
        worker = threading.current_thread().name
        with self.lock:
            self.task_status[task_id] = ("running", worker, 0)
        duration = random.uniform(1.0, 3.0)
        steps = 20
        for s in range(steps):
            time.sleep(duration / steps)
            with self.lock:
                self.task_status[task_id] = ("running", worker, (s + 1) / steps * 100)
        with self.lock:
            self.task_status[task_id] = ("done", worker, 100)

    def _poll(self):
        self.canvas.delete("all")
        cols = 4
        cell_w, cell_h = 160, 65
        x_pad, y_pad = 15, 10
        x_start, y_start = 20, 10

        for i, (tid, (status, worker, progress)) in enumerate(self.task_status.items()):
            col = i % cols
            row = i // cols
            x = x_start + col * (cell_w + x_pad)
            y = y_start + row * (cell_h + y_pad)

            if status == "done":
                bg = COLORS["green"]
                fg = COLORS["bg"]
            elif status == "running":
                bg = COLORS["blue"]
                fg = COLORS["bg"]
            else:
                bg = COLORS["surface"]
                fg = COLORS["text"]

            self.canvas.create_rectangle(x, y, x + cell_w, y + cell_h,
                                         fill=bg, outline=COLORS["subtext"])
            self.canvas.create_text(x + 5, y + 5, text=f"Task {tid}",
                                    fill=fg, font=("Menlo", 10, "bold"), anchor="nw")

            if status == "running":
                self.canvas.create_text(x + 5, y + 22,
                                        text=f"{worker.split('_')[-1]}",
                                        fill=fg, font=("Menlo", 9), anchor="nw")
                bar_x = x + 5
                bar_y = y + 40
                bar_w = cell_w - 10
                bar_h = 14
                self.canvas.create_rectangle(bar_x, bar_y, bar_x + bar_w, bar_y + bar_h,
                                             fill=COLORS["surface"], outline="")
                self.canvas.create_rectangle(bar_x, bar_y,
                                             bar_x + bar_w * progress / 100,
                                             bar_y + bar_h,
                                             fill=COLORS["yellow"], outline="")
                self.canvas.create_text(bar_x + bar_w // 2, bar_y + bar_h // 2,
                                        text=f"{int(progress)}%", fill=COLORS["bg"],
                                        font=("Menlo", 9))
            elif status == "done":
                self.canvas.create_text(x + cell_w // 2, y + 40, text="✅ Done",
                                        fill=fg, font=("Menlo", 11, "bold"))
            else:
                self.canvas.create_text(x + cell_w // 2, y + 40, text="⏳ Queued",
                                        fill=COLORS["subtext"], font=("Menlo", 11))

        done_count = sum(1 for s, _, _ in self.task_status.values() if s == "done")
        running_count = sum(1 for s, _, _ in self.task_status.values() if s == "running")
        self.stat_var.set(
            f"Running: {running_count} | Done: {done_count}/{len(self.task_status)}"
        )

        if self.running or done_count < len(self.task_status):
            self.after(80, self._poll)
        else:
            self.stat_var.set(f"All {len(self.task_status)} tasks completed! ✅")
            self.run_btn.config(state="normal")


class DiningPhilosophersDemo(ttk.Frame):
    """Tab 5: Classic Dining Philosophers visualization."""

    def __init__(self, parent):
        super().__init__(parent)
        self.n = 5
        self.running = False
        self.forks = [threading.Lock() for _ in range(self.n)]
        self.states = ["thinking"] * self.n  # thinking, hungry, eating
        self.eat_counts = [0] * self.n
        self.state_lock = threading.Lock()
        self._build_ui()

    def _build_ui(self):
        title = ttk.Label(self, text="🍝 Dining Philosophers", font=("Helvetica", 18, "bold"))
        title.pack(pady=(10, 0))
        desc = ttk.Label(
            self,
            text="5 philosophers sit at a round table. Each needs 2 forks to eat.\n"
                 "Demonstrates deadlock avoidance with resource ordering.",
            font=("Helvetica", 11), justify="center",
        )
        desc.pack(pady=(0, 10))

        self.canvas = tk.Canvas(
            self, width=500, height=350, bg=COLORS["bg"], highlightthickness=0
        )
        self.canvas.pack(padx=20, pady=5)

        ctrl = ttk.Frame(self)
        ctrl.pack(pady=5)
        self.start_btn = ttk.Button(ctrl, text="▶ Start", command=self.start)
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = ttk.Button(ctrl, text="⏹ Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        self.stat_var = tk.StringVar(value="Press Start to begin")
        ttk.Label(self, textvariable=self.stat_var, font=("Menlo", 11)).pack(pady=5)

        self._draw_table()

    def _draw_table(self):
        self.canvas.delete("all")
        import math
        cx, cy, r = 250, 175, 120

        self.canvas.create_oval(cx - 80, cy - 80, cx + 80, cy + 80,
                                fill=COLORS["surface"], outline=COLORS["subtext"], width=2)
        self.canvas.create_text(cx, cy, text="TABLE", fill=COLORS["subtext"],
                                font=("Menlo", 10))

        state_colors = {
            "thinking": COLORS["blue"],
            "hungry": COLORS["yellow"],
            "eating": COLORS["green"],
        }
        state_emoji = {
            "thinking": "🤔",
            "hungry": "😤",
            "eating": "🍝",
        }

        for i in range(self.n):
            angle = 2 * math.pi * i / self.n - math.pi / 2
            px = cx + r * math.cos(angle)
            py = cy + r * math.sin(angle)

            state = self.states[i]
            color = state_colors[state]

            self.canvas.create_oval(px - 25, py - 25, px + 25, py + 25,
                                    fill=color, outline="white", width=2)
            self.canvas.create_text(px, py - 5, text=state_emoji[state],
                                    font=("Helvetica", 16))
            self.canvas.create_text(px, py + 14, text=f"P{i}",
                                    fill=COLORS["bg"], font=("Menlo", 9, "bold"))

            lx = cx + (r + 45) * math.cos(angle)
            ly = cy + (r + 45) * math.sin(angle)
            self.canvas.create_text(lx, ly, text=f"ate:{self.eat_counts[i]}",
                                    fill=COLORS["text"], font=("Menlo", 9))

            # Every philosopher acquires the lower-numbered fork first. That
            # global ordering is the deadlock-avoidance rule this demo shows.
            fa = angle + math.pi / self.n
            fx = cx + 65 * math.cos(fa)
            fy = cy + 65 * math.sin(fa)
            self.canvas.create_text(fx, fy, text="🍴", font=("Helvetica", 16))

    def start(self):
        self.running = True
        self.states = ["thinking"] * self.n
        self.eat_counts = [0] * self.n
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        for i in range(self.n):
            threading.Thread(target=self._philosopher, args=(i,), daemon=True).start()
        self._poll()

    def _philosopher(self, pid):
        while self.running:
            with self.state_lock:
                self.states[pid] = "thinking"
            time.sleep(random.uniform(0.5, 1.5))

            with self.state_lock:
                self.states[pid] = "hungry"

            first = min(pid, (pid + 1) % self.n)
            second = max(pid, (pid + 1) % self.n)
            self.forks[first].acquire()
            time.sleep(0.1)
            self.forks[second].acquire()

            with self.state_lock:
                self.states[pid] = "eating"
                self.eat_counts[pid] += 1
            time.sleep(random.uniform(0.5, 1.0))

            self.forks[second].release()
            self.forks[first].release()

    def _poll(self):
        if not self.running:
            return
        self._draw_table()
        states_summary = ", ".join(
            f"P{i}:{s[:3]}" for i, s in enumerate(self.states)
        )
        self.stat_var.set(states_summary)
        self.after(100, self._poll)

    def stop(self):
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.stat_var.set("Stopped")


class GILExplainerDemo(ttk.Frame):
    """Tab 6: GIL explanation with CPU-bound vs I/O-bound comparison."""

    def __init__(self, parent):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        title = ttk.Label(self, text="🐍 Python GIL Explained", font=("Helvetica", 18, "bold"))
        title.pack(pady=(10, 0))

        self.canvas = tk.Canvas(
            self, width=700, height=300, bg=COLORS["bg"], highlightthickness=0
        )
        self.canvas.pack(padx=20, pady=10)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        self.io_btn = ttk.Button(btn_frame, text="⏱ Run I/O-bound Test",
                                 command=self.run_io_test)
        self.io_btn.pack(side="left", padx=5)
        self.cpu_btn = ttk.Button(btn_frame, text="⏱ Run CPU-bound Test",
                                  command=self.run_cpu_test)
        self.cpu_btn.pack(side="left", padx=5)

        self.result_var = tk.StringVar(
            value="Run tests to see threading vs sequential performance"
        )
        ttk.Label(self, textvariable=self.result_var, font=("Menlo", 11),
                  wraplength=650, justify="center").pack(pady=5)

        self._draw_explanation()

    def _draw_explanation(self):
        c = self.canvas
        c.delete("all")

        c.create_text(350, 20, text="Global Interpreter Lock (GIL)",
                      fill=COLORS["yellow"], font=("Helvetica", 14, "bold"))

        c.create_text(175, 55, text="I/O-Bound (threading HELPS ✅)",
                      fill=COLORS["green"], font=("Helvetica", 12, "bold"))
        y = 75
        for i in range(3):
            c.create_text(15, y + i * 30 + 10, text=f"T{i}", fill=COLORS["text"],
                          font=("Menlo", 10), anchor="w")
            for j in range(5):
                x = 45 + j * 65
                w = 25
                offset = i * 8
                c.create_rectangle(x + offset, y + i * 30, x + offset + w,
                                   y + i * 30 + 20,
                                   fill=THREAD_COLORS[i], outline="")
                if j < 4:
                    c.create_rectangle(x + offset + w, y + i * 30 + 5,
                                       x + offset + w + 35, y + i * 30 + 15,
                                       fill=COLORS["surface"], outline="",
                                       stipple="gray25")

        c.create_text(525, 55, text="CPU-Bound (threading NO help ❌)",
                      fill=COLORS["red"], font=("Helvetica", 12, "bold"))
        y = 75
        for i in range(3):
            c.create_text(390, y + i * 30 + 10, text=f"T{i}", fill=COLORS["text"],
                          font=("Menlo", 10), anchor="w")
            total_w = 250
            start_x = 415
            seg_start = start_x + i * (total_w // 3)
            seg_w = total_w // 3
            c.create_rectangle(start_x, y + i * 30, seg_start,
                               y + i * 30 + 20,
                               fill=COLORS["surface"], outline="")
            c.create_rectangle(seg_start, y + i * 30, seg_start + seg_w,
                               y + i * 30 + 20,
                               fill=THREAD_COLORS[i], outline="")
            c.create_rectangle(seg_start + seg_w, y + i * 30, start_x + total_w,
                               y + i * 30 + 20,
                               fill=COLORS["surface"], outline="")

        c.create_text(175, 190, text="█ = executing   ░ = waiting for I/O",
                      fill=COLORS["subtext"], font=("Menlo", 10))
        c.create_text(525, 190, text="█ = has GIL   ░ = waiting for GIL",
                      fill=COLORS["subtext"], font=("Menlo", 10))

        c.create_rectangle(50, 220, 650, 290, fill=COLORS["surface"],
                           outline=COLORS["mauve"], width=2)
        c.create_text(350, 240, text="💡 Key Takeaway:",
                      fill=COLORS["yellow"], font=("Helvetica", 12, "bold"))
        c.create_text(350, 262,
                      text="Use threading for I/O (network, file, sleep).",
                      fill=COLORS["text"], font=("Helvetica", 11))
        c.create_text(350, 280,
                      text="Use multiprocessing for CPU-heavy computation.",
                      fill=COLORS["text"], font=("Helvetica", 11))

    def run_io_test(self):
        self.io_btn.config(state="disabled")
        self.cpu_btn.config(state="disabled")
        self.result_var.set("Running I/O-bound test...")
        threading.Thread(target=self._io_test, daemon=True).start()

    def _io_test(self):
        def io_task():
            time.sleep(1)

        n = 5

        t0 = time.perf_counter()
        for _ in range(n):
            io_task()
        seq_time = time.perf_counter() - t0

        t0 = time.perf_counter()
        threads = [threading.Thread(target=io_task) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        thr_time = time.perf_counter() - t0

        speedup = seq_time / thr_time
        self.after(0, lambda: self.result_var.set(
            f"I/O-Bound: Sequential={seq_time:.2f}s | "
            f"Threaded={thr_time:.2f}s | "
            f"Speedup={speedup:.1f}x ⚡"
        ))
        self.after(0, lambda: self.io_btn.config(state="normal"))
        self.after(0, lambda: self.cpu_btn.config(state="normal"))

    def run_cpu_test(self):
        self.io_btn.config(state="disabled")
        self.cpu_btn.config(state="disabled")
        self.result_var.set("Running CPU-bound test... (may take a moment)")
        threading.Thread(target=self._cpu_test, daemon=True).start()

    def _cpu_test(self):
        def cpu_task():
            total = 0
            for i in range(2_000_000):
                total += i * i
            return total

        n = 4

        t0 = time.perf_counter()
        for _ in range(n):
            cpu_task()
        seq_time = time.perf_counter() - t0

        t0 = time.perf_counter()
        threads = [threading.Thread(target=cpu_task) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        thr_time = time.perf_counter() - t0

        ratio = thr_time / seq_time
        self.after(0, lambda: self.result_var.set(
            f"CPU-Bound: Sequential={seq_time:.2f}s | "
            f"Threaded={thr_time:.2f}s | "
            f"Ratio={ratio:.2f}x (>=1 = no benefit due to GIL) 🐌"
        ))
        self.after(0, lambda: self.io_btn.config(state="normal"))
        self.after(0, lambda: self.cpu_btn.config(state="normal"))


class MultithreadingDemoApp:
    def __init__(self, root):
        self.root = root
        root.title("🧵 Python Multithreading Visual Demo")
        root.geometry("760x560")
        root.configure(bg=COLORS["bg"])
        root.resizable(False, False)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=COLORS["bg"], foreground=COLORS["text"])
        style.configure("TNotebook", background=COLORS["bg"])
        style.configure("TNotebook.Tab", background=COLORS["surface"],
                        foreground=COLORS["text"], padding=[12, 4])
        style.map("TNotebook.Tab",
                  background=[("selected", COLORS["blue"])],
                  foreground=[("selected", COLORS["bg"])])
        style.configure("TButton", background=COLORS["surface"],
                        foreground=COLORS["text"], padding=[10, 4])
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
        style.configure("TScale", background=COLORS["bg"])

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)

        notebook.add(ThreadRaceDemo(notebook), text=" 🏁 Thread Race ")
        notebook.add(ProducerConsumerDemo(notebook), text=" 📦 Producer-Consumer ")
        notebook.add(RaceConditionDemo(notebook), text=" ⚠️ Race Condition ")
        notebook.add(ThreadPoolDemo(notebook), text=" 🏊 Thread Pool ")
        notebook.add(DiningPhilosophersDemo(notebook), text=" 🍝 Philosophers ")
        notebook.add(GILExplainerDemo(notebook), text=" 🐍 GIL Explained ")


if __name__ == "__main__":
    root = tk.Tk()
    app = MultithreadingDemoApp(root)
    root.mainloop()
