"""テスト専用の純粋インタープリタ(I/O なし)。本番は store.SqliteStore を使う。"""

from __future__ import annotations

from .domain import BallState, Event, fold
from .dsl import Emit, Load


class MemoryStore:
    def __init__(self, initial: BallState) -> None:
        self.state = initial
        self.log: list[Event] = []

    def handle(self, instr: object) -> object:
        if isinstance(instr, Load):
            return self.state
        if isinstance(instr, Emit):
            self.log.extend(instr.events)
            self.state = fold(self.state, instr.events)
            return None
        raise TypeError(f"unknown instruction: {instr!r}")
