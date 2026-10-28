import unittest

from fdmball.domain import (
    RADIUS,
    Axis,
    BallState,
    Bounced,
    Launch,
    Launched,
    Moved,
    Rejected,
    Tick,
    decide,
    evolve,
    fold,
    initial_state,
)


class Decide(unittest.TestCase):
    def test_invalid_dt_is_rejected(self) -> None:
        for dt in (0.0, -1.0, 0.5, float("nan"), float("inf")):
            self.assertEqual(decide(initial_state(), Tick(dt)), (Rejected("invalid_dt"),))

    def test_launch_validation(self) -> None:
        s = initial_state()
        self.assertIsInstance(decide(s, Launch(0.5, 0.5, 1.0, 1.0))[0], Launched)
        self.assertEqual(decide(s, Launch(0.0, 0.5, 1.0, 1.0)), (Rejected("launch_outside_field"),))
        self.assertEqual(decide(s, Launch(0.5, 0.5, 9.0, 1.0)), (Rejected("launch_too_fast"),))
        self.assertEqual(decide(s, Launch(float("nan"), 0.5, 1.0, 1.0)), (Rejected("non_finite_launch"),))

    def test_bounce_events(self) -> None:
        s = BallState(0, 1.0 - RADIUS - 0.001, 0.5, 1.0, 0.0)
        self.assertEqual(decide(s, Tick(0.1)), (Moved(0.1), Bounced(Axis.X)))


class Invariants(unittest.TestCase):
    def test_ball_never_leaves_field(self) -> None:
        for vx, vy, dt in ((3.0, 2.9, 0.1), (0.31, 0.47, 1 / 30), (-2.5, 1.7, 0.05), (0.0, -3.0, 0.1)):
            s = BallState(0, 0.37, 0.61, vx, vy)
            for _ in range(20_000):
                s = fold(s, decide(s, Tick(dt)))
                self.assertTrue(RADIUS <= s.x <= 1.0 - RADIUS, s)
                self.assertTrue(RADIUS <= s.y <= 1.0 - RADIUS, s)

    def test_rejected_does_not_change_state(self) -> None:
        s = initial_state()
        self.assertEqual(evolve(s, Rejected("x")), s)

    def test_n_is_monotonic(self) -> None:
        s = initial_state()
        for i in range(1, 100):
            s = fold(s, decide(s, Tick(0.01)))
            self.assertEqual(s.n, i)


if __name__ == "__main__":
    unittest.main()
