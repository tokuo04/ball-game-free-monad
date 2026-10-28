"""境界の変換(JSON ⇔ ドメイン値)。壊れた入力は例外でなく None で返す。"""

from __future__ import annotations

import json
from typing import cast

from .domain import RADIUS, Axis, BallState, Bounced, Event, Launch, Launched, Moved, Rejected


def _obj(text: str) -> dict[str, object] | None:
    try:
        raw: object = json.loads(text)
    except ValueError:
        return None
    if isinstance(raw, dict):
        return cast("dict[str, object]", raw)  # pyright: ignore[reportUnknownArgumentType]
    return None


def _num(d: dict[str, object], key: str) -> float | None:
    v = d.get(key)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v)


def encode_event(e: Event) -> tuple[str, str]:
    if isinstance(e, Moved):
        return "moved", json.dumps({"dt": e.dt})
    if isinstance(e, Bounced):
        return "bounced", json.dumps({"axis": e.axis.value})
    if isinstance(e, Launched):
        return "launched", json.dumps({"x": e.x, "y": e.y, "vx": e.vx, "vy": e.vy})
    return "rejected", json.dumps({"reason": e.reason})


def decode_event(kind: str, payload: str) -> Event | None:
    d = _obj(payload)
    if d is None:
        return None
    if kind == "moved":
        dt = _num(d, "dt")
        return None if dt is None else Moved(dt)
    if kind == "bounced":
        axis = d.get("axis")
        if axis == "x":
            return Bounced(Axis.X)
        if axis == "y":
            return Bounced(Axis.Y)
        return None
    if kind == "launched":
        v = _launch_values(d)
        return None if v is None else Launched(*v)
    if kind == "rejected":
        reason = d.get("reason")
        return Rejected(reason) if isinstance(reason, str) else None
    return None


def _launch_values(d: dict[str, object]) -> tuple[float, float, float, float] | None:
    x, y, vx, vy = _num(d, "x"), _num(d, "y"), _num(d, "vx"), _num(d, "vy")
    if x is None or y is None or vx is None or vy is None:
        return None
    return x, y, vx, vy


def encode_state(s: BallState) -> str:
    return json.dumps({"n": s.n, "x": s.x, "y": s.y, "vx": s.vx, "vy": s.vy})


def decode_state(text: str) -> BallState | None:
    d = _obj(text)
    if d is None:
        return None
    n = d.get("n")
    v = _launch_values(d)
    if isinstance(n, bool) or not isinstance(n, int) or v is None:
        return None
    return BallState(n, *v)


def decode_launch(text: str) -> Launch | None:
    d = _obj(text)
    v = None if d is None else _launch_values(d)
    return None if v is None else Launch(*v)


def to_wire(s: BallState, epoch: int, t_ms: int) -> dict[str, object]:
    """Firebase へ流す表現(短いキー)。e=起動ID, n=連番, t=サーバ時刻ms。"""
    return {"e": epoch, "n": s.n, "x": s.x, "y": s.y, "vx": s.vx, "vy": s.vy, "r": RADIUS, "t": t_ms}
