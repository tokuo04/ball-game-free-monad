import sqlite3
from typing import TypeVar
from domain import Free, Pure, Bind, GetState, SaveState, Ball, Position, Velocity

T = TypeVar('T')

class SQLiteFreeInterpreter:
    def __init__(self, db_path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS ball_state (
                    id TEXT PRIMARY KEY,
                    x REAL NOT NULL,
                    y REAL NOT NULL,
                    dx REAL NOT NULL,
                    dy REAL NOT NULL,
                    radius REAL NOT NULL
                )
            """)

    def run(self, program: Free[T]) -> T:
        curr = program
        while True:
            if isinstance(curr, Pure):
                return curr.value
            elif isinstance(curr, Bind):
                op = curr.op
                cont = curr.cont
                if isinstance(op, GetState):
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT id, x, y, dx, dy, radius FROM ball_state WHERE id = ?", (op.ball_id,))
                    row = cursor.fetchone()
                    if row:
                        ball = Ball(id=row[0], pos=Position(row[1], row[2]), vel=Velocity(row[3], row[4]), radius=row[5])
                    else:
                        ball = Ball(id=op.ball_id, pos=Position(400, 300), vel=Velocity(4, -4), radius=10.0)
                    curr = cont(ball)
                elif isinstance(op, SaveState):
                    with self.conn:
                        self.conn.execute("""
                            INSERT INTO ball_state (id, x, y, dx, dy, radius)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT(id) DO UPDATE SET
                                x=excluded.x, y=excluded.y, dx=excluded.dx, dy=excluded.dy
                        """, (op.ball.id, op.ball.pos.x, op.ball.pos.y, op.ball.vel.dx, op.ball.vel.dy, op.ball.radius))
                    curr = cont(None)  # type: ignore
                else:
                    raise RuntimeError("不明なオペレーション")
            else:
                raise TypeError("不正なFree構造です")
