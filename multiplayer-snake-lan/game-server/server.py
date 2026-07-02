"""FastAPI + websocket wrapper around game.py.

One authoritative Game instance. A background asyncio task runs the tick loop,
but only while at least one player is connected — an empty server burns zero CPU.
"""

import asyncio
import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from game import Game

TICK_SECONDS = 0.15  # ~6.7 ticks/sec

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("snake-server")

app = FastAPI()
game = Game()
players: dict[str, WebSocket] = {}
spectators: set[WebSocket] = set()
_tick_task: asyncio.Task | None = None


async def _broadcast(payload: dict):
    message = json.dumps(payload)
    stale = []
    for ws in list(players.values()) + list(spectators):
        try:
            await ws.send_text(message)
        except Exception:
            stale.append(ws)  # disconnect handlers do the real cleanup
    for ws in stale:
        spectators.discard(ws)


async def _tick_loop():
    log.info("tick loop started")
    try:
        while players:
            game.tick()
            await _broadcast({"type": "state", "data": game.state()})
            await asyncio.sleep(TICK_SECONDS)
    finally:
        log.info("tick loop stopped (no players connected)")


def _ensure_tick_loop():
    global _tick_task
    if _tick_task is None or _tick_task.done():
        _tick_task = asyncio.create_task(_tick_loop())


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "players": len(players),
        "spectators": len(spectators),
        "snakes": list(game.snakes.keys()),
    }


@app.websocket("/play/{snake_id}")
async def play(ws: WebSocket, snake_id: str):
    await ws.accept()
    if snake_id in players or not game.add_snake(snake_id):
        await ws.send_text(json.dumps({"type": "error", "message": "snake id taken or board full"}))
        await ws.close()
        return
    players[snake_id] = ws
    _ensure_tick_loop()
    log.info("player joined: %s (%d connected)", snake_id, len(players))
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "direction":
                game.set_direction(snake_id, msg.get("direction"))
    except WebSocketDisconnect:
        pass
    finally:
        players.pop(snake_id, None)
        game.remove_snake(snake_id)
        log.info("player left: %s (%d connected)", snake_id, len(players))


@app.websocket("/watch")
async def watch(ws: WebSocket):
    await ws.accept()
    spectators.add(ws)
    log.info("spectator joined (%d watching)", len(spectators))
    try:
        # Send a snapshot immediately so the board renders before the next tick.
        await ws.send_text(json.dumps({"type": "state", "data": game.state()}))
        while True:
            await ws.receive_text()  # spectators are read-only; ignore input
    except WebSocketDisconnect:
        pass
    finally:
        spectators.discard(ws)
        log.info("spectator left (%d watching)", len(spectators))
