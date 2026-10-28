"""命令的シェル: 時計・HTTP制御口・Firebase配信だけを持つ。ドメインは一切知らない。"""

from __future__ import annotations

import argparse
import json
import os
import queue
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Sequence

from .codec import decode_launch, to_wire
from .domain import BallState, Command, Tick, initial_state
from .dsl import handle_command
from .free import run
from .publish import FirebasePublisher
from .store import SqliteStore


class Shared:
    """メインループが書き、HTTP スレッドが読む最新状態(ロック付き)。"""

    def __init__(self, state: BallState, epoch: int) -> None:
        self._lock = threading.Lock()
        self._state = state
        self.epoch = epoch

    def set(self, state: BallState) -> None:
        with self._lock:
            self._state = state

    def get(self) -> BallState:
        with self._lock:
            return self._state


def bind_free_port_server(shared: Shared, commands: "queue.Queue[Command]") -> ThreadingHTTPServer:
    """ポート 0 で bind し、OS が割り当てた空きポートを使う(調べてから bind する競合がない)。"""

    class Handler(BaseHTTPRequestHandler):
        def _reply(self, code: int, body: dict[str, object]) -> None:
            data = json.dumps(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if self.path == "/state":
                self._reply(200, to_wire(shared.get(), shared.epoch, int(time.time() * 1000)))
            elif self.path == "/health":
                self._reply(200, {"ok": True})
            else:
                self._reply(404, {"error": "not_found"})

        def do_POST(self) -> None:
            if self.path != "/launch":
                self._reply(404, {"error": "not_found"})
                return
            length = min(int(self.headers.get("Content-Length", "0") or "0"), 1024)
            launch = decode_launch(self.rfile.read(length).decode("utf-8", "replace"))
            if launch is None:
                self._reply(400, {"error": "bad_launch"})
                return
            commands.put(launch)  # 検証はドメイン(decide)が行い、不正なら Rejected になる
            self._reply(202, {"queued": True})

        def log_message(self, format: str, *args: object) -> None:
            return

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="fdmball")
    p.add_argument("--db-url", default=os.environ.get("FIREBASE_DB_URL", ""), help="Firebase RTDB の URL")
    p.add_argument("--room", default="main")
    p.add_argument("--sqlite", default="fdm_ball.sqlite3")
    p.add_argument("--reset", action="store_true", help="SQLite を初期化して始める")
    p.add_argument("--hz", type=int, default=30, help="シミュレーション周波数")
    p.add_argument("--publish-every", type=int, default=3, help="何ティックごとに配信するか")
    args = p.parse_args(argv)
    if not args.db_url:
        print("--db-url か環境変数 FIREBASE_DB_URL を指定してください", file=sys.stderr)
        return 2

    def log(message: str) -> None:
        print(message, flush=True)

    hz: int = args.hz
    every: int = args.publish_every
    dt = 1.0 / hz
    epoch = int(time.time())
    store = SqliteStore(args.sqlite, initial_state(), reset=args.reset)
    state = run(handle_command(Tick(dt)), store.handle)  # 復元後の最初の状態
    shared = Shared(state, epoch)
    commands: "queue.Queue[Command]" = queue.Queue()
    server = bind_free_port_server(shared, commands)
    port = int(server.server_address[1])
    threading.Thread(target=server.serve_forever, name="control", daemon=True).start()

    publisher = FirebasePublisher(args.db_url, args.room, os.environ.get("FIREBASE_AUTH"), log)
    publisher.start()
    publisher.put_now("meta", {"e": epoch, "port": port, "hz": hz, "t": int(time.time() * 1000)})
    log(f"control http: 127.0.0.1:{port}  room={args.room}  epoch={epoch}")

    counter = 0
    next_at = time.monotonic()
    try:
        while True:
            while True:
                try:
                    cmd = commands.get_nowait()
                except queue.Empty:
                    break
                run(handle_command(cmd), store.handle)
            state = run(handle_command(Tick(dt)), store.handle)
            shared.set(state)
            counter = (counter + 1) % every
            if counter == 0:
                publisher.submit(to_wire(state, epoch, int(time.time() * 1000)))
            next_at += dt
            delay = next_at - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            elif delay < -1.0:  # 大きく遅れたら追いつかず仕切り直す
                next_at = time.monotonic()
    except KeyboardInterrupt:
        log("stopping")
    finally:
        server.shutdown()
        server.server_close()
        publisher.close()
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
