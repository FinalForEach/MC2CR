"""Background thread worker for executing world conversions without freezing the GUI."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from mc2cr.converter import convert_mc_world


@dataclass
class ProgressEvent:
    """Event sent from worker thread to update GUI progress."""

    item_name: str
    current: int
    total: int
    phase: str
    elapsed_str: str
    eta_str: str
    percentage: float


@dataclass
class LogEvent:
    """Event sent from worker thread to append a log line."""

    message: str
    level: str = "info"


@dataclass
class CompleteEvent:
    """Event sent when conversion successfully completes."""

    stats: Dict[str, Any]


@dataclass
class ErrorEvent:
    """Event sent when an error occurs during conversion."""

    error_message: str


class ConversionWorker(threading.Thread):
    """Thread worker that performs the world conversion asynchronously."""

    def __init__(
        self,
        input_path: Path,
        output_path: Path,
        y_offset: int = -64,
        max_workers: Optional[int] = None,
        mapping_override: Optional[str] = None,
        event_queue: Optional[queue.Queue] = None,
    ) -> None:
        super().__init__(daemon=True)
        self.input_path = input_path
        self.output_path = output_path
        self.y_offset = y_offset
        self.max_workers = max_workers
        self.mapping_override = mapping_override
        self.event_queue = event_queue or queue.Queue()

        self._start_time = 0.0
        self._phase_start_time = 0.0
        self._current_phase = "convert"

    def run(self) -> None:
        """Execute the conversion and send status updates to the event queue."""
        self._start_time = time.time()
        self._phase_start_time = time.time()
        self._current_phase = "convert"

        self.event_queue.put(LogEvent(f"Starting conversion of '{self.input_path.name}'..."))
        self.event_queue.put(LogEvent(f"Source: {self.input_path}"))
        self.event_queue.put(LogEvent(f"Destination: {self.output_path}"))
        self.event_queue.put(LogEvent(f"Y-Offset: {self.y_offset} blocks"))

        def progress_callback(item_name: str, current: int, total: int, phase: str = "convert") -> None:
            now = time.time()
            if phase != self._current_phase:
                self._current_phase = phase
                self._phase_start_time = now
                phase_label = "Saving Cosmic Reach regions" if phase == "save" else "Converting Minecraft chunks"
                self.event_queue.put(LogEvent(f"--- Phase: {phase_label} ({total} total) ---"))

            elapsed = now - self._phase_start_time
            remaining = total - current
            avg_time = elapsed / current if current > 0 else 0
            eta_seconds = int(avg_time * remaining)

            if eta_seconds >= 60:
                eta_str = f"{eta_seconds // 60}m {eta_seconds % 60:02d}s"
            else:
                eta_str = f"{eta_seconds}s"

            elapsed_total = now - self._start_time
            if elapsed_total >= 60:
                elapsed_str = f"{int(elapsed_total // 60)}m {int(elapsed_total % 60):02d}s"
            else:
                elapsed_str = f"{int(elapsed_total)}s"

            pct = (current / total * 100.0) if total > 0 else 0.0

            event = ProgressEvent(
                item_name=item_name,
                current=current,
                total=total,
                phase=phase,
                elapsed_str=elapsed_str,
                eta_str=eta_str,
                percentage=pct,
            )
            self.event_queue.put(event)

        try:
            stats = convert_mc_world(
                mc_world_dir=self.input_path,
                cr_world_dir=self.output_path,
                mapping_override=self.mapping_override,
                progress_callback=progress_callback,
                y_offset=self.y_offset,
                max_workers=self.max_workers,
            )
            self.event_queue.put(CompleteEvent(stats=stats))
        except Exception as e:
            self.event_queue.put(ErrorEvent(error_message=str(e)))
