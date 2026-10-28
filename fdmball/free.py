"""汎用 Free モナド(ドメイン非依存・スタック安全)。

命令の型は意図的に ``object`` とし、解釈はハンドラ側が行う。
``bind`` は常に ``Bind`` ノードを作るだけで評価せず、``run`` が明示的な
継続スタックで畳み込むため、左結合の深いチェーンでも再帰しない。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar, Union, cast

A = TypeVar("A")
B = TypeVar("B")

Handler = Callable[[object], object]


@dataclass(frozen=True)
class Pure(Generic[A]):
    value: A


@dataclass(frozen=True)
class Do(Generic[A]):
    """命令 1 つの実行。結果の型 A は幽霊型(スマートコンストラクタが保証)。"""

    instr: object


@dataclass(frozen=True)
class Bind(Generic[A]):
    src: Free[object]
    f: Callable[[object], Free[A]]


Free = Union[Pure[A], Do[A], Bind[A]]


def pure(value: A) -> Free[A]:
    return Pure(value)


def bind(m: Free[A], f: Callable[[A], Free[B]]) -> Free[B]:
    return Bind(cast("Free[object]", m), cast("Callable[[object], Free[B]]", f))


def fmap(m: Free[A], f: Callable[[A], B]) -> Free[B]:
    return bind(m, lambda a: pure(f(a)))


def then(m: Free[A], n: Free[B]) -> Free[B]:
    return bind(m, lambda _: n)


def run(program: Free[A], handler: Handler) -> A:
    """プログラムをハンドラで実行する。ループ+継続スタックなので再帰しない。"""
    stack: list[Callable[[object], Free[object]]] = []
    current: Free[object] = cast("Free[object]", program)
    while True:
        if isinstance(current, Bind):
            stack.append(current.f)
            current = current.src
            continue
        value: object = current.value if isinstance(current, Pure) else handler(current.instr)
        if not stack:
            return cast(A, value)
        current = stack.pop()(value)
