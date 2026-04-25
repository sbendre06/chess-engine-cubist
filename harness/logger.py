"""Per-search perf logger for the frozen harness.

Writes one CSV row per `go` command with runtime perf data (depth, nodes,
nps, search_elapsed_ms). Tokens/time for generating the engine code live
elsewhere: engines/<name>.tokens.csv written by the agent at session end.
"""

from __future__ import annotations

import csv
import os
import threading
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.engine import SearchResult


DEFAULT_LOG_PATH = Path("logs/harness_perf.csv")


class ExperimentLogger:
    fieldnames = [
        "timestamp_utc",
        "session_id",
        "engine_name",
        "session_elapsed_s",
        "search_elapsed_ms",
        "depth_completed",
        "nodes",
        "nps",
        "score_cp",
        "bestmove",
        "stopped",
        "turn",
        "fen",
    ]

    def __init__(self, *, engine_name: str) -> None:
        self.session_id = uuid.uuid4().hex[:12]
        self.session_started = time.perf_counter()
        self.engine_name = engine_name
        self.log_path = Path(os.getenv("CUBIST_LOG_PATH", str(DEFAULT_LOG_PATH)))
        self._lock = threading.Lock()

    def log_search(
        self,
        *,
        fen: str,
        turn: str,
        result: "SearchResult",
        bestmove: str,
    ) -> None:
        row = {
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "session_id": self.session_id,
            "engine_name": self.engine_name,
            "session_elapsed_s": round(time.perf_counter() - self.session_started, 3),
            "search_elapsed_ms": result.elapsed_ms,
            "depth_completed": result.depth_completed,
            "nodes": result.nodes,
            "nps": result.nps,
            "score_cp": result.score_cp,
            "bestmove": bestmove,
            "stopped": int(result.stopped),
            "turn": turn,
            "fen": fen,
        }

        with self._lock:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            file_exists = self.log_path.exists()
            with self.log_path.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=self.fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
