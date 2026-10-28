import os
import tempfile
import unittest

from fdmball.domain import Command, Launch, Tick, initial_state
from fdmball.dsl import handle_command
from fdmball.free import run
from fdmball.memory import MemoryStore
from fdmball.store import SNAPSHOT_EVERY, SqliteStore



def _commands() -> list[Command]:
    cmds: list[Command] = [Tick(1 / 30) for _ in range(500)]
    cmds.append(Launch(0.2, 0.8, -1.5, 0.9))
    cmds.extend(Tick(1 / 30) for _ in range(500))
    return cmds


COMMANDS = _commands()


class Contract(unittest.TestCase):
    """メモリ版と SQLite 版は同じプログラムに同じ結果を返す。"""

    def test_same_result(self) -> None:
        mem = MemoryStore(initial_state())
        with tempfile.TemporaryDirectory() as d:
            sql = SqliteStore(os.path.join(d, "t.sqlite3"), initial_state())
            for cmd in COMMANDS:
                a = run(handle_command(cmd), mem.handle)
                b = run(handle_command(cmd), sql.handle)
                self.assertEqual(a, b)
            sql.close()


class Recovery(unittest.TestCase):
    def test_restore_from_snapshot_plus_replay(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.sqlite3")
            first = SqliteStore(path, initial_state())
            last = initial_state()
            for _ in range(SNAPSHOT_EVERY * 3 + 7):  # スナップショット間隔の途中で止める
                last = run(handle_command(Tick(1 / 30)), first.handle)
            first.close()
            second = SqliteStore(path, initial_state())
            restored = run(handle_command(Tick(1 / 30)), second.handle)
            expected = run(handle_command(Tick(1 / 30)), MemoryStore(last).handle)
            self.assertEqual(restored, expected)
            second.close()

    def test_reset_starts_fresh(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.sqlite3")
            first = SqliteStore(path, initial_state())
            for _ in range(200):
                run(handle_command(Tick(1 / 30)), first.handle)
            first.close()
            fresh = SqliteStore(path, initial_state(), reset=True)
            self.assertEqual(run(handle_command(Tick(1 / 30)), fresh.handle).n, 1)
            fresh.close()


if __name__ == "__main__":
    unittest.main()
