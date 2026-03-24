#!/usr/bin/env python3
"""
Qt-based multithreading demo.

Run:
    python3 multithread_demo_qt.py

This implementation prefers PySide6 and falls back to PyQt6.
"""

from __future__ import annotations

import queue
import random
import sys
import threading
import time
from dataclasses import dataclass

try:
    from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, QTimer, Signal
    from PySide6.QtWidgets import (
        QApplication,
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QPushButton,
        QProgressBar,
        QSpinBox,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
    QT_BINDING = "PySide6"
except ImportError:
    try:
        from PyQt6.QtCore import QObject, QRunnable, QThreadPool, Qt, QTimer, pyqtSignal as Signal
        from PyQt6.QtWidgets import (
            QApplication,
            QFrame,
            QGridLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QMainWindow,
            QPushButton,
            QProgressBar,
            QSpinBox,
            QTabWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
        QT_BINDING = "PyQt6"
    except ImportError as exc:
        raise SystemExit(
            "This demo requires PySide6 or PyQt6. Install one of them, and make sure "
            "a Qt binding is installed for python3 before running the file."
        ) from exc


COLORS = {
    "bg": "#1e1e2e",
    "surface": "#313244",
    "surface_alt": "#45475a",
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
    COLORS["red"],
    COLORS["green"],
    COLORS["blue"],
    COLORS["yellow"],
    COLORS["mauve"],
    COLORS["teal"],
    COLORS["peach"],
    COLORS["pink"],
    COLORS["sky"],
    COLORS["lavender"],
]


def card_frame() -> QFrame:
    frame = QFrame()
    frame.setObjectName("Card")
    return frame


def set_progress_color(bar: QProgressBar, color: str) -> None:
    bar.setStyleSheet(
        f"""
        QProgressBar {{
            border: 1px solid {COLORS["surface_alt"]};
            border-radius: 6px;
            background: {COLORS["surface"]};
            color: {COLORS["bg"]};
            text-align: center;
            min-height: 22px;
        }}
        QProgressBar::chunk {{
            background: {color};
            border-radius: 5px;
        }}
        """
    )


class ThreadRaceTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.num_threads = 6
        self.running = False
        self._winner_announced = False
        self.lock = threading.Lock()
        self.progress_values = {i: 0.0 for i in range(self.num_threads)}
        self.bars: list[QProgressBar] = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_progress)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.addWidget(self._title("Thread Race"))
        root.addWidget(self._description(
            "Each worker thread increments its own progress value at random speeds. "
            "The UI stays on the Qt main thread and polls shared state with a timer."
        ))

        group = card_frame()
        group_layout = QVBoxLayout(group)
        for index in range(self.num_threads):
            row = QHBoxLayout()
            label = QLabel(f"Thread-{index}")
            label.setMinimumWidth(90)
            label.setStyleSheet(f"color: {THREAD_COLORS[index]}; font-weight: 700;")

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            set_progress_color(bar, THREAD_COLORS[index])
            row.addWidget(label)
            row.addWidget(bar, 1)
            self.bars.append(bar)
            group_layout.addLayout(row)
        root.addWidget(group)

        controls = QHBoxLayout()
        self.start_btn = QPushButton("Start Race")
        self.start_btn.clicked.connect(self.start_race)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset)
        controls.addWidget(self.start_btn)
        controls.addWidget(self.reset_btn)
        controls.addStretch(1)
        root.addLayout(controls)

        self.status_label = QLabel("Ready - press Start")
        root.addWidget(self.status_label)
        root.addStretch(1)

    def _title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size: 22px; font-weight: 700;")
        return label

    def _description(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {COLORS['subtext']};")
        return label

    def start_race(self) -> None:
        if self.running:
            return
        self.reset()
        self.running = True
        self.start_btn.setEnabled(False)
        self.status_label.setText("Racing...")
        for tid in range(self.num_threads):
            thread = threading.Thread(target=self._worker, args=(tid,), daemon=True)
            thread.start()
        self.timer.start(30)

    def _worker(self, tid: int) -> None:
        while self.running:
            with self.lock:
                current = self.progress_values[tid]
            if current >= 100:
                return
            time.sleep(random.uniform(0.01, 0.08))
            with self.lock:
                self.progress_values[tid] = min(100.0, current + random.uniform(0.5, 3.0))

    def _poll_progress(self) -> None:
        with self.lock:
            snapshot = dict(self.progress_values)

        finished = []
        for tid, value in snapshot.items():
            self.bars[tid].setValue(int(value))
            if value >= 100:
                finished.append(tid)

        if finished and not self._winner_announced:
            self._winner_announced = True
            self.status_label.setText(f"Thread-{finished[0]} finished first. Waiting for others...")

        if len(finished) == self.num_threads:
            self.running = False
            self.timer.stop()
            self.status_label.setText(f"Thread-{finished[0]} wins!")
            self.start_btn.setEnabled(True)

    def reset(self) -> None:
        self.running = False
        self.timer.stop()
        self._winner_announced = False
        with self.lock:
            for key in self.progress_values:
                self.progress_values[key] = 0.0
        for bar in self.bars:
            bar.setValue(0)
        self.start_btn.setEnabled(True)
        self.status_label.setText("Ready - press Start")

    def stop(self) -> None:
        self.running = False
        self.timer.stop()


class ProducerConsumerTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.running = False
        self.buffer = queue.Queue(maxsize=10)
        self.buffer_items: list[int] = []
        self.lock = threading.Lock()
        self.produced = 0
        self.consumed = 0
        self.slots: list[QLabel] = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.addWidget(self._title("Producer-Consumer"))
        root.addWidget(self._description(
            "Producers push values into a bounded queue. Consumers remove them. "
            "Qt renders a mirror of queue contents while Python threads handle the work."
        ))

        controls = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop)
        self.stop_btn.setEnabled(False)

        self.producers_spin = QSpinBox()
        self.producers_spin.setRange(1, 5)
        self.producers_spin.setValue(2)
        self.consumers_spin = QSpinBox()
        self.consumers_spin.setRange(1, 5)
        self.consumers_spin.setValue(2)

        controls.addWidget(self.start_btn)
        controls.addWidget(self.stop_btn)
        controls.addWidget(QLabel("Producers"))
        controls.addWidget(self.producers_spin)
        controls.addWidget(QLabel("Consumers"))
        controls.addWidget(self.consumers_spin)
        controls.addStretch(1)
        root.addLayout(controls)

        buffer_box = QGroupBox("Buffer (max 10)")
        buffer_layout = QHBoxLayout(buffer_box)
        for _ in range(10):
            slot = QLabel(" ")
            slot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slot.setMinimumSize(48, 48)
            slot.setStyleSheet(
                f"background: {COLORS['surface']}; border: 1px solid {COLORS['surface_alt']};"
                " border-radius: 8px; font-weight: 700;"
            )
            buffer_layout.addWidget(slot)
            self.slots.append(slot)
        root.addWidget(buffer_box)

        self.status_label = QLabel("Produced: 0 | Consumed: 0 | Buffer: 0/10")
        root.addWidget(self.status_label)
        root.addStretch(1)

    def _title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size: 22px; font-weight: 700;")
        return label

    def _description(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {COLORS['subtext']};")
        return label

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.produced = 0
        self.consumed = 0
        with self.lock:
            self.buffer_items.clear()
        while not self.buffer.empty():
            try:
                self.buffer.get_nowait()
            except queue.Empty:
                break

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        for idx in range(self.producers_spin.value()):
            threading.Thread(target=self._producer, args=(idx,), daemon=True).start()
        for idx in range(self.consumers_spin.value()):
            threading.Thread(target=self._consumer, args=(idx,), daemon=True).start()
        self.timer.start(100)

    def _producer(self, producer_id: int) -> None:
        while self.running:
            item = random.randint(1, 99)
            try:
                self.buffer.put(item, timeout=0.5)
                with self.lock:
                    self.buffer_items.append(item)
                    self.produced += 1
            except queue.Full:
                pass
            time.sleep(random.uniform(0.3, 0.8))

    def _consumer(self, consumer_id: int) -> None:
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

    def _poll(self) -> None:
        if not self.running:
            return
        with self.lock:
            snapshot = list(self.buffer_items[:10])
            produced = self.produced
            consumed = self.consumed
        for index, slot in enumerate(self.slots):
            if index < len(snapshot):
                slot.setText(str(snapshot[index]))
                slot.setStyleSheet(
                    f"background: {COLORS['peach']}; color: {COLORS['bg']};"
                    f" border: 1px solid {COLORS['yellow']}; border-radius: 8px; font-weight: 700;"
                )
            else:
                slot.setText(" ")
                slot.setStyleSheet(
                    f"background: {COLORS['surface']}; border: 1px solid {COLORS['surface_alt']};"
                    " border-radius: 8px; font-weight: 700;"
                )
        self.status_label.setText(
            f"Produced: {produced} | Consumed: {consumed} | Buffer: {len(snapshot)}/10"
        )

    def stop(self) -> None:
        self.running = False
        self.timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)


class RaceConditionSignals(QObject):
    finished = Signal(int, int, int)


class RaceConditionTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.counter_no_lock = 0
        self.counter_with_lock = 0
        self.lock = threading.Lock()
        self.signals = RaceConditionSignals()
        self.signals.finished.connect(self._show_results)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.addWidget(self._title("Race Condition Demo"))
        root.addWidget(self._description(
            "Ten threads increment a shared counter 100,000 times. The first run omits locking, "
            "the second wraps the increment in a lock."
        ))

        grid = QGridLayout()
        left = card_frame()
        right = card_frame()
        left_layout = QVBoxLayout(left)
        right_layout = QVBoxLayout(right)

        left_layout.addWidget(QLabel("WITHOUT Lock"))
        self.no_lock_value = QLabel("?")
        self.no_lock_value.setStyleSheet(f"font-size: 36px; color: {COLORS['red']}; font-weight: 700;")
        self.no_lock_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.no_lock_value)
        self.no_lock_verdict = QLabel("")
        self.no_lock_verdict.setWordWrap(True)
        left_layout.addWidget(self.no_lock_verdict)

        right_layout.addWidget(QLabel("WITH Lock"))
        self.with_lock_value = QLabel("?")
        self.with_lock_value.setStyleSheet(f"font-size: 36px; color: {COLORS['green']}; font-weight: 700;")
        self.with_lock_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.with_lock_value)
        self.with_lock_verdict = QLabel("")
        self.with_lock_verdict.setWordWrap(True)
        right_layout.addWidget(self.with_lock_verdict)

        grid.addWidget(left, 0, 0)
        grid.addWidget(right, 0, 1)
        root.addLayout(grid)

        self.run_btn = QPushButton("Run Experiment")
        self.run_btn.clicked.connect(self.run_experiment)
        root.addWidget(self.run_btn)

        self.status_label = QLabel("Press Run to begin")
        root.addWidget(self.status_label)
        root.addStretch(1)

    def _title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size: 22px; font-weight: 700;")
        return label

    def _description(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {COLORS['subtext']};")
        return label

    def run_experiment(self) -> None:
        self.run_btn.setEnabled(False)
        self.status_label.setText("Running... (10 threads x 100,000 increments)")
        self.no_lock_value.setText("?")
        self.with_lock_value.setText("?")
        self.no_lock_verdict.setText("")
        self.with_lock_verdict.setText("")
        threading.Thread(target=self._experiment, daemon=True).start()

    def _experiment(self) -> None:
        num_threads = 10
        increments = 100_000
        expected = num_threads * increments

        self.counter_no_lock = 0

        def inc_no_lock() -> None:
            for _ in range(increments):
                self.counter_no_lock += 1

        threads = [threading.Thread(target=inc_no_lock) for _ in range(num_threads)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        result_no_lock = self.counter_no_lock

        self.counter_with_lock = 0

        def inc_with_lock() -> None:
            for _ in range(increments):
                with self.lock:
                    self.counter_with_lock += 1

        threads = [threading.Thread(target=inc_with_lock) for _ in range(num_threads)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        result_with_lock = self.counter_with_lock
        self.signals.finished.emit(result_no_lock, result_with_lock, expected)

    def _show_results(self, no_lock: int, with_lock: int, expected: int) -> None:
        self.no_lock_value.setText(f"{no_lock:,}")
        self.with_lock_value.setText(f"{with_lock:,}")
        if no_lock != expected:
            self.no_lock_verdict.setText(f"Wrong: off by {expected - no_lock:,}")
            self.no_lock_verdict.setStyleSheet(f"color: {COLORS['red']};")
        else:
            self.no_lock_verdict.setText("Correct, but only because this run got lucky.")
            self.no_lock_verdict.setStyleSheet(f"color: {COLORS['yellow']};")

        if with_lock == expected:
            self.with_lock_verdict.setText("Correct result with explicit locking.")
            self.with_lock_verdict.setStyleSheet(f"color: {COLORS['green']};")
        else:
            self.with_lock_verdict.setText("Unexpected error.")
            self.with_lock_verdict.setStyleSheet(f"color: {COLORS['red']};")
        self.status_label.setText("Done. Run again to compare another timing outcome.")
        self.run_btn.setEnabled(True)


class PoolTaskSignals(QObject):
    update = Signal(int, str, str, int)


class PoolTask(QRunnable):
    def __init__(self, task_id: int, signals: PoolTaskSignals) -> None:
        super().__init__()
        self.task_id = task_id
        self.signals = signals

    def run(self) -> None:
        worker = threading.current_thread().name
        self.signals.update.emit(self.task_id, "running", worker, 0)
        duration = random.uniform(1.0, 3.0)
        steps = 20
        for step in range(steps):
            time.sleep(duration / steps)
            self.signals.update.emit(
                self.task_id,
                "running",
                worker,
                int((step + 1) / steps * 100),
            )
        self.signals.update.emit(self.task_id, "done", worker, 100)


@dataclass
class TaskCard:
    container: QFrame
    title: QLabel
    worker: QLabel
    progress: QProgressBar
    status: QLabel


class ThreadPoolTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.pool = QThreadPool(self)
        self.signals = PoolTaskSignals()
        self.signals.update.connect(self._handle_task_update)
        self.task_cards: dict[int, TaskCard] = {}
        self.task_state: dict[int, tuple[str, str, int]] = {}
        self.total_tasks = 12
        self.done_count = 0
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.addWidget(self._title("Thread Pool"))
        root.addWidget(self._description(
            "This tab uses Qt's QThreadPool and QRunnable to process a fixed set of tasks. "
            "Each task emits progress updates back to the UI thread."
        ))

        controls = QHBoxLayout()
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 6)
        self.workers_spin.setValue(3)
        self.run_btn = QPushButton("Submit 12 Tasks")
        self.run_btn.clicked.connect(self.submit_tasks)
        controls.addWidget(QLabel("Workers"))
        controls.addWidget(self.workers_spin)
        controls.addWidget(self.run_btn)
        controls.addStretch(1)
        root.addLayout(controls)

        grid = QGridLayout()
        for task_id in range(self.total_tasks):
            card = card_frame()
            layout = QVBoxLayout(card)
            title = QLabel(f"Task {task_id}")
            title.setStyleSheet("font-weight: 700;")
            worker = QLabel("Queued")
            worker.setStyleSheet(f"color: {COLORS['subtext']};")
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(0)
            set_progress_color(progress, COLORS["yellow"])
            status = QLabel("Queued")
            layout.addWidget(title)
            layout.addWidget(worker)
            layout.addWidget(progress)
            layout.addWidget(status)
            self.task_cards[task_id] = TaskCard(card, title, worker, progress, status)
            grid.addWidget(card, task_id // 4, task_id % 4)
        root.addLayout(grid)

        self.status_label = QLabel("Configure workers and submit tasks")
        root.addWidget(self.status_label)
        root.addStretch(1)

    def _title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size: 22px; font-weight: 700;")
        return label

    def _description(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {COLORS['subtext']};")
        return label

    def submit_tasks(self) -> None:
        if self.done_count < self.total_tasks and self.task_state:
            return
        self.pool.setMaxThreadCount(self.workers_spin.value())
        self.done_count = 0
        self.task_state.clear()
        self.run_btn.setEnabled(False)
        for task_id, card in self.task_cards.items():
            self.task_state[task_id] = ("pending", "", 0)
            card.worker.setText("Queued")
            card.progress.setValue(0)
            card.status.setText("Queued")
            card.container.setStyleSheet("")
        for task_id in range(self.total_tasks):
            self.pool.start(PoolTask(task_id, self.signals))
        self._refresh_status()

    def _handle_task_update(self, task_id: int, status: str, worker: str, progress: int) -> None:
        self.task_state[task_id] = (status, worker, progress)
        card = self.task_cards[task_id]
        if status == "running":
            card.worker.setText(worker)
            card.progress.setValue(progress)
            card.status.setText(f"Running - {progress}%")
            card.container.setStyleSheet(f"#Card {{ background: {COLORS['blue']}; border-radius: 12px; }}")
        elif status == "done":
            previous_status = self.task_state.get(task_id, ("pending", "", 0))[0]
            if previous_status != "done":
                self.done_count = sum(1 for state, _, _ in self.task_state.values() if state == "done")
            card.worker.setText(worker)
            card.progress.setValue(100)
            card.status.setText("Done")
            card.container.setStyleSheet(f"#Card {{ background: {COLORS['green']}; border-radius: 12px; }}")
        self._refresh_status()

    def _refresh_status(self) -> None:
        running = sum(1 for state, _, _ in self.task_state.values() if state == "running")
        done = sum(1 for state, _, _ in self.task_state.values() if state == "done")
        if done == self.total_tasks and self.task_state:
            self.status_label.setText(f"All {self.total_tasks} tasks completed.")
            self.run_btn.setEnabled(True)
            self.done_count = self.total_tasks
        else:
            self.status_label.setText(f"Running: {running} | Done: {done}/{self.total_tasks}")


class DiningPhilosophersTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.n = 5
        self.running = False
        self.forks = [threading.Lock() for _ in range(self.n)]
        self.states = ["thinking"] * self.n
        self.eat_counts = [0] * self.n
        self.state_lock = threading.Lock()
        self.cards: list[tuple[QLabel, QLabel]] = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.addWidget(self._title("Dining Philosophers"))
        root.addWidget(self._description(
            "Each philosopher needs two forks. The demo avoids deadlock by always acquiring the "
            "lower-numbered fork first."
        ))

        controls = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop)
        self.stop_btn.setEnabled(False)
        controls.addWidget(self.start_btn)
        controls.addWidget(self.stop_btn)
        controls.addStretch(1)
        root.addLayout(controls)

        grid = QGridLayout()
        for philosopher_id in range(self.n):
            box = QGroupBox(f"Philosopher {philosopher_id}")
            layout = QVBoxLayout(box)
            state = QLabel("thinking")
            count = QLabel("Meals: 0")
            state.setStyleSheet(f"font-size: 18px; color: {COLORS['blue']};")
            layout.addWidget(state)
            layout.addWidget(count)
            self.cards.append((state, count))
            grid.addWidget(box, philosopher_id // 3, philosopher_id % 3)
        root.addLayout(grid)

        self.status_label = QLabel("Press Start to begin")
        root.addWidget(self.status_label)
        root.addStretch(1)

    def _title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size: 22px; font-weight: 700;")
        return label

    def _description(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {COLORS['subtext']};")
        return label

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        with self.state_lock:
            self.states = ["thinking"] * self.n
            self.eat_counts = [0] * self.n
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        for philosopher_id in range(self.n):
            threading.Thread(target=self._philosopher, args=(philosopher_id,), daemon=True).start()
        self.timer.start(100)

    def _philosopher(self, philosopher_id: int) -> None:
        while self.running:
            with self.state_lock:
                self.states[philosopher_id] = "thinking"
            time.sleep(random.uniform(0.5, 1.5))

            with self.state_lock:
                self.states[philosopher_id] = "hungry"

            first = min(philosopher_id, (philosopher_id + 1) % self.n)
            second = max(philosopher_id, (philosopher_id + 1) % self.n)
            self.forks[first].acquire()
            time.sleep(0.1)
            self.forks[second].acquire()

            with self.state_lock:
                self.states[philosopher_id] = "eating"
                self.eat_counts[philosopher_id] += 1
            time.sleep(random.uniform(0.5, 1.0))

            self.forks[second].release()
            self.forks[first].release()

    def _poll(self) -> None:
        if not self.running:
            return
        with self.state_lock:
            states = list(self.states)
            counts = list(self.eat_counts)
        color_map = {
            "thinking": COLORS["blue"],
            "hungry": COLORS["yellow"],
            "eating": COLORS["green"],
        }
        for idx, (state_label, count_label) in enumerate(self.cards):
            state = states[idx]
            state_label.setText(state)
            state_label.setStyleSheet(f"font-size: 18px; color: {color_map[state]};")
            count_label.setText(f"Meals: {counts[idx]}")
        summary = ", ".join(f"P{idx}:{state[:3]}" for idx, state in enumerate(states))
        self.status_label.setText(summary)

    def stop(self) -> None:
        self.running = False
        self.timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Stopped")


class GILSignals(QObject):
    finished = Signal(str)
    started = Signal(str)


class GILExplainerTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.signals = GILSignals()
        self.signals.finished.connect(self._set_result)
        self.signals.started.connect(self._set_result)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.addWidget(self._title("Python GIL Explained"))

        explainer = QTextEdit()
        explainer.setReadOnly(True)
        explainer.setPlainText(
            "I/O-bound tasks benefit from threading because threads often wait on external events.\n\n"
            "CPU-bound tasks do not usually speed up under normal CPython threading because the "
            "Global Interpreter Lock allows only one thread to execute Python bytecode at a time.\n\n"
            "Use threading for network, file, and timer-heavy work.\n"
            "Use multiprocessing or native extensions for CPU-heavy work."
        )
        explainer.setMinimumHeight(180)
        root.addWidget(explainer)

        controls = QHBoxLayout()
        self.io_btn = QPushButton("Run I/O-bound Test")
        self.io_btn.clicked.connect(self.run_io_test)
        self.cpu_btn = QPushButton("Run CPU-bound Test")
        self.cpu_btn.clicked.connect(self.run_cpu_test)
        controls.addWidget(self.io_btn)
        controls.addWidget(self.cpu_btn)
        controls.addStretch(1)
        root.addLayout(controls)

        self.result_label = QLabel("Run tests to compare sequential and threaded execution.")
        self.result_label.setWordWrap(True)
        root.addWidget(self.result_label)
        root.addStretch(1)

    def _title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size: 22px; font-weight: 700;")
        return label

    def run_io_test(self) -> None:
        self._set_buttons_enabled(False)
        self.signals.started.emit("Running I/O-bound test...")
        threading.Thread(target=self._io_test, daemon=True).start()

    def _io_test(self) -> None:
        def io_task() -> None:
            time.sleep(1)

        n = 5
        start = time.perf_counter()
        for _ in range(n):
            io_task()
        sequential = time.perf_counter() - start

        start = time.perf_counter()
        threads = [threading.Thread(target=io_task) for _ in range(n)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        threaded = time.perf_counter() - start
        speedup = sequential / threaded
        self.signals.finished.emit(
            f"I/O-bound: Sequential={sequential:.2f}s | Threaded={threaded:.2f}s | Speedup={speedup:.1f}x"
        )

    def run_cpu_test(self) -> None:
        self._set_buttons_enabled(False)
        self.signals.started.emit("Running CPU-bound test...")
        threading.Thread(target=self._cpu_test, daemon=True).start()

    def _cpu_test(self) -> None:
        def cpu_task() -> int:
            total = 0
            for i in range(2_000_000):
                total += i * i
            return total

        n = 4
        start = time.perf_counter()
        for _ in range(n):
            cpu_task()
        sequential = time.perf_counter() - start

        start = time.perf_counter()
        threads = [threading.Thread(target=cpu_task) for _ in range(n)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        threaded = time.perf_counter() - start
        ratio = threaded / sequential
        self.signals.finished.emit(
            f"CPU-bound: Sequential={sequential:.2f}s | Threaded={threaded:.2f}s | Ratio={ratio:.2f}x"
        )

    def _set_result(self, text: str) -> None:
        self.result_label.setText(text)
        if not text.startswith("Running"):
            self._set_buttons_enabled(True)

    def _set_buttons_enabled(self, enabled: bool) -> None:
        self.io_btn.setEnabled(enabled)
        self.cpu_btn.setEnabled(enabled)


class MultithreadingDemoWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Python Multithreading Demo ({QT_BINDING})")
        self.resize(1100, 820)

        tabs = QTabWidget()
        self.thread_race_tab = ThreadRaceTab()
        self.producer_consumer_tab = ProducerConsumerTab()
        self.race_condition_tab = RaceConditionTab()
        self.thread_pool_tab = ThreadPoolTab()
        self.dining_philosophers_tab = DiningPhilosophersTab()
        self.gil_tab = GILExplainerTab()

        tabs.addTab(self.thread_race_tab, "Thread Race")
        tabs.addTab(self.producer_consumer_tab, "Producer-Consumer")
        tabs.addTab(self.race_condition_tab, "Race Condition")
        tabs.addTab(self.thread_pool_tab, "Thread Pool")
        tabs.addTab(self.dining_philosophers_tab, "Philosophers")
        tabs.addTab(self.gil_tab, "GIL Explained")
        self.setCentralWidget(tabs)

        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{
                background: {COLORS["bg"]};
                color: {COLORS["text"]};
                font-size: 14px;
            }}
            QTabWidget::pane {{
                border: 1px solid {COLORS["surface_alt"]};
                border-radius: 10px;
                background: {COLORS["bg"]};
            }}
            QTabBar::tab {{
                background: {COLORS["surface"]};
                color: {COLORS["text"]};
                padding: 10px 16px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background: {COLORS["blue"]};
                color: {COLORS["bg"]};
            }}
            QPushButton {{
                background: {COLORS["surface"]};
                border: 1px solid {COLORS["surface_alt"]};
                border-radius: 8px;
                padding: 8px 14px;
            }}
            QPushButton:disabled {{
                color: {COLORS["subtext"]};
                background: {COLORS["surface_alt"]};
            }}
            QGroupBox, #Card {{
                background: {COLORS["surface"]};
                border: 1px solid {COLORS["surface_alt"]};
                border-radius: 12px;
                margin-top: 8px;
                padding: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
            QSpinBox, QTextEdit {{
                background: {COLORS["surface"]};
                border: 1px solid {COLORS["surface_alt"]};
                border-radius: 6px;
                padding: 4px;
            }}
            """
        )

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.thread_race_tab.stop()
        self.producer_consumer_tab.stop()
        self.dining_philosophers_tab.stop()
        self.thread_pool_tab.pool.waitForDone()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    window = MultithreadingDemoWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
