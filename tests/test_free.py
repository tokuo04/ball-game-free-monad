import unittest

from fdmball.domain import initial_state
from fdmball.dsl import emit, load
from fdmball.domain import Tick, decide
from fdmball.free import Free, bind, pure, run
from fdmball.memory import MemoryStore


def _exec(program: Free[int]) -> tuple[int, int]:
    store = MemoryStore(initial_state())
    result = run(program, store.handle)
    return result, len(store.log)


def _f(x: int) -> Free[int]:
    return bind(load(), lambda s: bind(emit(decide(s, Tick(0.01))), lambda _: pure(x + 1)))


def _g(x: int) -> Free[int]:
    return bind(emit(decide(initial_state(), Tick(0.02))), lambda _: pure(x * 2))


class MonadLaws(unittest.TestCase):
    def test_left_identity(self) -> None:
        self.assertEqual(_exec(bind(pure(3), _f)), _exec(_f(3)))

    def test_right_identity(self) -> None:
        m = _f(3)
        self.assertEqual(_exec(bind(m, pure)), _exec(m))

    def test_associativity(self) -> None:
        m = _f(3)
        left = bind(bind(m, _g), _f)
        right = bind(m, lambda x: bind(_g(x), _f))
        self.assertEqual(_exec(left), _exec(right))


class StackSafety(unittest.TestCase):
    def test_deep_left_nested_bind(self) -> None:
        program: Free[int] = pure(0)
        for _ in range(100_000):
            program = bind(program, lambda x: pure(x + 1))
        self.assertEqual(run(program, MemoryStore(initial_state()).handle), 100_000)


if __name__ == "__main__":
    unittest.main()
