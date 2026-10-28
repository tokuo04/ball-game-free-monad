from typing import Generic, TypeVar, Callable, NamedTuple
from dataclasses import dataclass

T = TypeVar('T')
A = TypeVar('A')

class Position(NamedTuple):
    x: float
    y: float

class Velocity(NamedTuple):
    dx: float
    dy: float

@dataclass(frozen=True)
class Ball:
    id: str
    pos: Position
    vel: Velocity
    radius: float = 10.0

    def step(self, width: float, height: float) -> 'Ball':
        nx = self.pos.x + self.vel.dx
        ny = self.pos.y + self.vel.dy
        ndx = self.vel.dx
        ndy = self.vel.dy
        if nx - self.radius <= 0 or nx + self.radius >= width:
            ndx = -ndx
            nx = max(self.radius, min(width - self.radius, nx))
        if ny - self.radius <= 0 or ny + self.radius >= height:
            ndy = -ndy
            ny = max(self.radius, min(height - self.radius, ny))
        return Ball(id=self.id, pos=Position(nx, ny), vel=Velocity(ndx, ndy), radius=self.radius)

class BallOp(Generic[A]): pass

class GetState(BallOp[Ball]):
    def __init__(self, ball_id: str) -> None:
        self.ball_id = ball_id

class SaveState(BallOp[None]):
    def __init__(self, ball: Ball) -> None:
        self.ball = ball

class Free(Generic[T]): pass

class Pure(Free[T]):
    def __init__(self, value: T) -> None:
        self.value = value

class Bind(Free[T], Generic[A, T]):
    def __init__(self, op: BallOp[A], cont: Callable[[A], Free[T]]) -> None:
        self.op = op
        self.cont = cont
