"""純粋ドメイン層: Command → (decide) → Event → (evolve) → State。副作用なし。

座標は論理座標 0.0–1.0(画素変換はブラウザ側)。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from enum import Enum
from typing import NoReturn, Union

RADIUS = 0.02
MAX_DT = 0.1
MAX_SPEED = 3.0  # MAX_DT * MAX_SPEED < 1 - 2*RADIUS なので 1 ステップの反射は高々 1 回


class Axis(Enum):
    X = "x"
    Y = "y"


@dataclass(frozen=True)
class BallState:
    n: int  # Moved の適用回数(単調増加。受信側の順序判定に使う)
    x: float
    y: float
    vx: float
    vy: float


@dataclass(frozen=True)
class Tick:
    dt: float


@dataclass(frozen=True)
class Launch:
    x: float
    y: float
    vx: float
    vy: float


Command = Union[Tick, Launch]


@dataclass(frozen=True)
class Moved:
    dt: float


@dataclass(frozen=True)
class Bounced:
    axis: Axis


@dataclass(frozen=True)
class Launched:
    x: float
    y: float
    vx: float
    vy: float


@dataclass(frozen=True)
class Rejected:
    reason: str


Event = Union[Moved, Bounced, Launched, Rejected]


def initial_state() -> BallState:
    return BallState(n=0, x=0.5, y=0.5, vx=0.31, vy=0.47)


def _inside(p: float) -> bool:
    return RADIUS <= p <= 1.0 - RADIUS


def _out(p: float) -> bool:
    return p < RADIUS or p > 1.0 - RADIUS


def _absurd(x: NoReturn) -> NoReturn:
    raise AssertionError(f"unhandled: {x!r}")


def decide(state: BallState, cmd: Command) -> tuple[Event, ...]:
    """状態とコマンドからイベント列を決める。不正入力は Rejected イベントで表す。"""
    if isinstance(cmd, Tick):
        if not (math.isfinite(cmd.dt) and 0.0 < cmd.dt <= MAX_DT):
            return (Rejected("invalid_dt"),)
        nx = state.x + state.vx * cmd.dt
        ny = state.y + state.vy * cmd.dt
        events: list[Event] = [Moved(cmd.dt)]
        if _out(nx):
            events.append(Bounced(Axis.X))
        if _out(ny):
            events.append(Bounced(Axis.Y))
        return tuple(events)
    values = (cmd.x, cmd.y, cmd.vx, cmd.vy)
    if not all(math.isfinite(v) for v in values):
        return (Rejected("non_finite_launch"),)
    if not (_inside(cmd.x) and _inside(cmd.y)):
        return (Rejected("launch_outside_field"),)
    if abs(cmd.vx) > MAX_SPEED or abs(cmd.vy) > MAX_SPEED:
        return (Rejected("launch_too_fast"),)
    return (Launched(cmd.x, cmd.y, cmd.vx, cmd.vy),)


def _reflect(p: float) -> float:
    lo, hi = RADIUS, 1.0 - RADIUS
    if p < lo:
        p = 2.0 * lo - p
    elif p > hi:
        p = 2.0 * hi - p
    return min(max(p, lo), hi)


def evolve(state: BallState, event: Event) -> BallState:
    """イベントを状態へ適用する唯一の関数(全イベントを網羅)。"""
    if isinstance(event, Moved):
        return replace(
            state,
            n=state.n + 1,
            x=state.x + state.vx * event.dt,
            y=state.y + state.vy * event.dt,
        )
    if isinstance(event, Bounced):
        if event.axis is Axis.X:
            return replace(state, x=_reflect(state.x), vx=-state.vx)
        return replace(state, y=_reflect(state.y), vy=-state.vy)
    if isinstance(event, Launched):
        return replace(state, x=event.x, y=event.y, vx=event.vx, vy=event.vy)
    if isinstance(event, Rejected):
        return state
    return _absurd(event)


def fold(state: BallState, events: tuple[Event, ...]) -> BallState:
    for event in events:
        state = evolve(state, event)
    return state
