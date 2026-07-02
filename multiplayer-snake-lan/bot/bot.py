"""Greedy snake bot. One container = one bot = one genuinely isolated player.

Reads SERVER_URL and SNAKE_ID from env, connects to /play/{SNAKE_ID},
and every tick picks the safe direction that closes the most Manhattan
distance to the nearest food. Reconnects with backoff if the server drops.
"""

import asyncio
import json
import os
import random

import websockets

SERVER_URL = os.environ.get("SERVER_URL", "ws://localhost:8000")
SNAKE_ID = os.environ.get("SNAKE_ID", f"bot-{random.randint(1000, 9999)}")

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}


def decide(state, my_id):
    """Rank the four directions by distance to the nearest food, drop unsafe ones."""
    me = state["snakes"].get(my_id)
    if not me or not me["body"]:
        return None
    hx, hy = me["body"][0]
    current = me["direction"]

    # Cells that mean death next tick: every snake's body minus each tail
    # (the tail cell vacates as the snake moves).
    occupied = set()
    for snake in state["snakes"].values():
        body = [tuple(c) for c in snake["body"]]
        occupied.update(body[:-1] if len(body) > 1 else body)

    food = [tuple(c) for c in state["food"]]
    target = min(food, key=lambda f: abs(f[0] - hx) + abs(f[1] - hy)) if food else None

    def score(direction):
        dx, dy = DIRS[direction]
        nx, ny = hx + dx, hy + dy
        if not (0 <= nx < state["width"] and 0 <= ny < state["height"]):
            return None  # wall
        if (nx, ny) in occupied:
            return None  # body
        if target is None:
            return 0
        return abs(target[0] - nx) + abs(target[1] - ny)

    options = []
    for direction in DIRS:
        if len(me["body"]) > 1 and direction == OPPOSITE[current]:
            continue  # server rejects reversals anyway; don't waste the move
        s = score(direction)
        if s is not None:
            options.append((s, random.random(), direction))  # random tiebreak

    if not options:
        return current  # boxed in — hold course and take the respawn
    return min(options)[2]


async def play_once():
    url = f"{SERVER_URL}/play/{SNAKE_ID}"
    async with websockets.connect(url) as ws:
        print(f"[{SNAKE_ID}] connected to {url}", flush=True)
        async for raw in ws:
            msg = json.loads(raw)
            if msg.get("type") == "error":
                print(f"[{SNAKE_ID}] server refused: {msg.get('message')}", flush=True)
                return
            if msg.get("type") != "state":
                continue
            direction = decide(msg["data"], SNAKE_ID)
            if direction:
                await ws.send(json.dumps({"type": "direction", "direction": direction}))


async def main():
    backoff = 1
    while True:
        try:
            await play_once()
            backoff = 1  # clean session — reset
        except (OSError, websockets.WebSocketException) as exc:
            print(f"[{SNAKE_ID}] connection lost ({exc!r}), retrying in {backoff}s", flush=True)
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 10)


if __name__ == "__main__":
    asyncio.run(main())
