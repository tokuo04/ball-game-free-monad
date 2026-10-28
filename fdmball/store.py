"""SQLite インタープリタ: Free プログラムの唯一の永続化の入口。

events: 追記専用ログ。snapshot: last_seq 付きの射影(一定間隔で更新)。
復元 = snapshot + (last_seq より後のイベントの再生)。
"""

from __future__ import annotations

import sqlite3
from typing import cast

from .codec import decode_event, decode_state, encode_event, encode_state
from .domain import BallState, Event, fold
from .dsl import Emit, Load

SNAPSHOT_EVERY = 60  # イベント数
KEEP_EVENTS = 600  # スナップショットより前に残すイベント数(メモリ/ディスクの上限管理)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events(
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshot(
  id INTEGER PRIMARY KEY CHECK (id = 1),
  last_seq INTEGER NOT NULL,
  state TEXT NOT NULL
);
"""


class SqliteStore:
    def __init__(self, path: str, initial: BallState, *, reset: bool = False) -> None:
        self._conn = sqlite3.connect(path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        if reset:
            self._conn.executescript("DROP TABLE IF EXISTS events; DROP TABLE IF EXISTS snapshot;")
        self._conn.executescript(_SCHEMA)
        self._state, self._last_seq, self._snap_seq = self._recover(initial)

    def _recover(self, initial: BallState) -> tuple[BallState, int, int]:
        row: tuple[int, str] | None = self._conn.execute(
            "SELECT last_seq, state FROM snapshot WHERE id = 1"
        ).fetchone()
        if row is None:
            state, snap_seq = initial, 0
        else:
            decoded = decode_state(row[1])
            if decoded is None:  # 壊れたスナップショットは捨てて初期化する
                self._conn.executescript("DELETE FROM events; DELETE FROM snapshot;")
                return initial, 0, 0
            state, snap_seq = decoded, row[0]
        last = snap_seq
        cursor = self._conn.execute(
            "SELECT seq, kind, payload FROM events WHERE seq > ? ORDER BY seq", (snap_seq,)
        )
        for raw in cursor:
            seq, kind, payload = cast("tuple[int, str, str]", raw)
            event = decode_event(kind, payload)
            if event is None:  # 壊れたログはそこで再生を止める
                break
            state = fold(state, (event,))
            last = seq
        return state, last, snap_seq

    def handle(self, instr: object) -> object:
        if isinstance(instr, Load):
            return self._state
        if isinstance(instr, Emit):
            self._append(instr.events)
            return None
        raise TypeError(f"unknown instruction: {instr!r}")

    def _append(self, events: tuple[Event, ...]) -> None:
        if not events:
            return
        new_state = fold(self._state, events)
        with self._conn:  # 1 コマンド = 1 トランザクション(原子的)
            last = self._last_seq
            for event in events:
                kind, payload = encode_event(event)
                rowid = self._conn.execute(
                    "INSERT INTO events(kind, payload) VALUES (?, ?)", (kind, payload)
                ).lastrowid
                if rowid is None:
                    raise RuntimeError("INSERT returned no rowid")
                last = rowid
            snap_seq = self._snap_seq
            if last - snap_seq >= SNAPSHOT_EVERY:
                self._conn.execute(
                    "INSERT INTO snapshot(id, last_seq, state) VALUES (1, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET last_seq = excluded.last_seq, state = excluded.state",
                    (last, encode_state(new_state)),
                )
                self._conn.execute("DELETE FROM events WHERE seq <= ?", (last - KEEP_EVENTS,))
                snap_seq = last
        self._state, self._last_seq, self._snap_seq = new_state, last, snap_seq

    def close(self) -> None:
        self._conn.close()
