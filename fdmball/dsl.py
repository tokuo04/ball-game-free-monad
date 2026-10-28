"""ボール用 DSL(命令)とプログラム。命令は 2 つだけ: Load / Emit。

状態の保存は Emit(イベント追記)に一本化し、状態はイベントの射影として得る。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from .domain import BallState, Command, Event, decide, fold
from .free import Do, Free, bind, pure, then


@dataclass(frozen=True)
class Load:
    """現在の状態を得る。"""


@dataclass(frozen=True)
class Emit:
    """イベントを追記する(状態はその射影)。"""

    events: tuple[Event, ...]


Instruction = Union[Load, Emit]


def load() -> Free[BallState]:
    return Do[BallState](Load())


def emit(events: tuple[Event, ...]) -> Free[None]:
    return Do[None](Emit(events))


def handle_command(cmd: Command) -> Free[BallState]:
    """Load → decide(純粋) → Emit → 新しい状態。再利用可能な値としてのプログラム。"""

    def after_load(state: BallState) -> Free[BallState]:
        events = decide(state, cmd)
        return then(emit(events), pure(fold(state, events)))

    return bind(load(), after_load)
