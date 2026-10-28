"""Firebase Realtime Database への配信(REST/標準ライブラリのみ)。

送信側も「最新1件のみ」保持する。回線が詰まっても古い状態は溜めず捨てる。
"""

from __future__ import annotations

import json
import threading
import urllib.parse
import urllib.request
from typing import Callable


class FirebasePublisher:
    def __init__(self, db_url: str, room: str, auth: str | None, log: Callable[[str], None]) -> None:
        self._base = db_url.rstrip("/")
        self._room = urllib.parse.quote(room, safe="")
        self._auth = auth
        self._log = log
        self._slot: dict[str, object] | None = None
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="publisher", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def submit(self, payload: dict[str, object]) -> None:
        with self._lock:
            self._slot = payload  # 未送信の古い値は上書きされて捨てられる
        self._wake.set()

    def put_now(self, name: str, payload: dict[str, object]) -> None:
        try:
            self._put(name, payload)
        except OSError as exc:
            self._log(f"publish {name} failed: {exc}")

    def close(self) -> None:
        self._stop.set()
        self._wake.set()
        self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(1.0)
            with self._lock:
                payload, self._slot = self._slot, None
                self._wake.clear()
            if payload is None:
                continue
            try:
                self._put("state", payload)
            except OSError as exc:
                self._log(f"publish failed: {exc}")
                self._stop.wait(1.0)

    def _put(self, name: str, payload: dict[str, object]) -> None:
        query = f"?auth={urllib.parse.quote(self._auth, safe='')}" if self._auth else ""
        url = f"{self._base}/rooms/{self._room}/{name}.json{query}"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            method="PUT",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            response.read()
