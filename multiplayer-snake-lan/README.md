# Multiplayer Snake in a Box

> Most Docker demos prove containers *can* talk. This one gives them a reason to.

Four bots play snake against each other on one authoritative server, and every player is genuinely its own container — own process, own decision loop, own lifecycle. Run `docker ps` while it's going and every container on screen is doing real work. Stop one mid-game and the server doesn't blink; the dead snake just vanishes from the board.

## Quick start

```bash
git clone https://github.com/Arhamurrahemeen/Dockerrr.git
cd Dockerrr/multiplayer-snake-lan
docker-compose up --build
```

Then open [http://localhost:8080](http://localhost:8080) and watch four snakes fight over food.

Or don't just watch — type a name, hit join, and steer with arrows/WASD (swipe on a phone). Anyone on your LAN can open `http://<your-ip>:8080` and jump in against the bots too. That's the `-lan` part of the name earning its keep.

Try killing one:

```bash
docker stop multiplayer-snake-lan-bot-3-1
```

The other three keep playing. That's the whole point.

## Architecture

Six containers, three images:

| Container | What it does |
|---|---|
| `game-server` | Owns all state — snake positions, food, collisions. Runs an asyncio tick loop (~7 ticks/sec) *only while players are connected*, and broadcasts the full board to every client each tick. |
| `bot-1` … `bot-4` | Independent Python processes. Each connects over websocket as its own player, runs greedy pathing (move toward nearest food, don't die doing it), and reconnects with backoff if the server drops. |
| `spectator` | nginx serving one static page. It connects to the server's read-only `/watch` endpoint and renders the live board on a canvas. Has a join box — humans connect to the same `/play` endpoint the bots use, with zero special treatment. |

The server is the single source of truth — bots only send direction inputs, they never touch state. Endpoints:

- `ws://…:8000/play/{snake_id}` — join as a player
- `ws://…:8000/watch` — spectate, read-only
- `http://…:8000/health` — player/spectator counts

Game logic lives in [game.py](game-server/game.py) with zero networking in it, so it's testable on its own. [server.py](game-server/server.py) is just the websocket wrapper around it.

Snakes respawn when they die (score resets, death counter ticks up) so the board never goes quiet during a demo.

## Stack

*As of July 2026 — the architecture doesn't care which versions these are.*

- Python 3.12, FastAPI + uvicorn (server), websockets (bots)
- nginx alpine (spectator)
- Docker Compose, healthcheck-gated startup so bots wait for the server

— Arham
