import asyncio
from typing import Dict, Optional
from domain import Ball

class ReceiverConflator:
    def __init__(self) -> None:
      self._latest_state: Dict[str, Ball] = {}
      self._lock = asyncio.Lock()

    async def push(self, ball: Ball) -> None:
        async with self._lock:
            self._latest_state[ball.id] = ball

    async def pop_latest(self, ball_id: str) -> Optional[Ball]:
        async with self._lock:
            return self._latest_state.pop(ball_id, None)
