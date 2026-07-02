# Build Spec: Multiplayer Snake in a Box

Hand this file to Claude Code in the repo. Target location: `builds/multiplayer-snake-lan/`.

## Why this build exists

Most Docker portfolio projects are a tutorial with the serial numbers filed off — a `docker-compose.yml` with two containers saying hello to each other. That proves containers *can* talk. It doesn't prove anything about why you'd want them to.

This build uses Docker for something that actually needs it: a multiplayer game where every player genuinely is an isolated process, not a thread pretending. One authoritative server, N independent bot containers, one spectator view. If you `docker ps` while it's running, every container on screen is doing real work.

This is the first entry in the new `builds/` folder — fast, fun, standalone projects, distinct from the reflective `playbooks/` and `philosophies/` pieces elsewhere in the repo.

## Design status

The architecture and core logic below were already designed and unit-tested in a prior session (pure Python, no Docker available in that sandbox). The design is validated:
- Core game logic (movement, collision, food, wall detection) ran 50 ticks clean with no state corruption.
- Bot pathing logic (greedy-toward-food, wall/collision avoidance) tested against hand-built board states — correctly avoids walls, correctly seeks food.
- The full websocket loop (server ↔ two simultaneous bot clients) was run locally in that sandbox: both bots connected, joined, and the server confirmed live player count.

What's untested: the actual `docker-compose up --build` flow end to end, since that sandbox had no Docker daemon. **That's the one thing this session needs to verify for real.**

## Architecture

```
game-server (FastAPI + websockets, asyncio tick loop, ~6-7 ticks/sec)
  - owns all state: snake positions, food, collisions
  - broadcasts full board state to every connected client every tick
  - /play/{snake_id} — websocket endpoint for bots/players (accepts direction input)
  - /watch — websocket endpoint for spectators (read-only)
  - /health — plain HTTP status endpoint

bot (Python, websockets client) x4
  - each is its own container, own process, own decision loop
  - greedy pathing: move toward food, avoid immediate wall/collision death
  - env vars: SERVER_URL, SNAKE_ID
  - independently reconnects if the server drops

spectator (static HTML + canvas, served via python http.server or nginx)
  - connects to /watch, renders the live board
  - styled with the repo's own palette (cream/ink/teal/muted — see CONTEXT.md §4), not default Docker-tutorial styling
```

## File structure to produce

```
builds/multiplayer-snake-lan/
├── README.md
├── docker-compose.yml
├── game-server/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── game.py       # pure game logic, no networking
│   └── server.py      # FastAPI/websocket wrapper around game.py
├── bot/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── bot.py
└── spectator/
    ├── Dockerfile
    └── index.html
```

## Requirements per file

**`game.py`** — pure logic, testable without any networking. Board width/height, snake as list of `(x, y)` cells, direction handling with 180-degree-reversal prevention, wall collision, self/other-snake collision (excluding the tail cell that's about to move), food spawn/respawn, score tracking. Expose a `state()` method returning JSON-serializable dict.

**`server.py`** — FastAPI app. Asyncio background task runs the tick loop only while at least one player is connected. Broadcasts `{"type": "state", "data": game.state()}` to all connected players + spectators every tick. Handles disconnects cleanly (remove snake, don't crash the loop).

**`bot.py`** — connects via `websockets`, reads `SERVER_URL` and `SNAKE_ID` from env, greedy-pathing decision function (rank the 4 directions by Manhattan distance to food, reject unsafe ones, pick the best safe option), reconnect-with-backoff if the connection drops.

**`index.html`** — canvas rendering of board state, connects to `/watch`, styled with the repo palette (cream background, teal accent bars, Georgia italic heading, Courier New labels — pull exact values from `CONTEXT.md` §4). Show live scoreboard per snake.

**`docker-compose.yml`** — `game-server` service exposing 8000, `spectator` exposing 8080→80, four `bot` services (or one scalable bot service) all depending on `game-server`, each bot with a distinct `SNAKE_ID`.

## Acceptance criteria

- [ ] `docker-compose up --build` succeeds with no errors.
- [ ] `docker ps` shows 6 running containers (server, spectator, 4 bots) — this is the screenshot/clip moment.
- [ ] Opening `http://localhost:8080` shows a live-updating board with 4 distinctly colored snakes moving.
- [ ] Killing one bot container (`docker stop <bot-container>`) doesn't crash the server or the other bots — the dead snake just disappears from the board.
- [ ] `curl http://localhost:8000/health` returns player/spectator counts.

## README requirements

Follow the lightweight build-README pattern (not the full `CONTEXT.md` long-form piece structure — builds don't need a banner SVG or hero diagram, just clean and functional):
- One-line pull-quote framing why this exists (tutorial vs. real use, per the "Why this build exists" section above).
- Quick-start: clone, `docker-compose up --build`, open localhost:8080.
- Architecture section explaining what each container does.
- "Stack" section clearly marked as the dated layer.
- Closing signature: `— Arham`.

## After it runs

Record 15–20 seconds: the spectator board with bots moving, split-screen or cut to a `docker ps` terminal showing the separate containers. That clip is the LinkedIn/Instagram asset — don't over-produce it, the raw demo is the point.
