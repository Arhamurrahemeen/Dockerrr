"""Pure game logic for multiplayer snake. No networking, no asyncio — testable in isolation.

The server owns one Game instance and calls tick() on a fixed interval.
Everything here is synchronous and deterministic given the RNG.
"""

import random

BOARD_W = 32
BOARD_H = 24
START_LEN = 3
FOOD_COUNT = 3
MAX_SNAKES = 8

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}


class Snake:
    def __init__(self, snake_id, color_slot, head):
        self.id = snake_id
        self.color_slot = color_slot
        self.body = [head]  # body[0] is the head
        self.direction = random.choice(list(DIRS))
        self.pending_growth = START_LEN - 1  # grow into starting length
        self.score = 0
        self.deaths = 0


class Game:
    def __init__(self, width=BOARD_W, height=BOARD_H, food_count=FOOD_COUNT, rng=None):
        self.width = width
        self.height = height
        self.food_count = food_count
        self.rng = rng or random.Random()
        self.snakes = {}  # snake_id -> Snake
        self.food = []    # list of (x, y)
        self._free_slots = list(range(MAX_SNAKES))
        self._top_up_food()

    # -- membership ----------------------------------------------------------

    def add_snake(self, snake_id):
        if snake_id in self.snakes or not self._free_slots:
            return False
        head = self._random_free_cell()
        if head is None:
            return False
        slot = self._free_slots.pop(0)
        self.snakes[snake_id] = Snake(snake_id, slot, head)
        return True

    def remove_snake(self, snake_id):
        snake = self.snakes.pop(snake_id, None)
        if snake:
            self._free_slots.insert(0, snake.color_slot)
            self._free_slots.sort()

    def set_direction(self, snake_id, direction):
        snake = self.snakes.get(snake_id)
        if not snake or direction not in DIRS:
            return
        # 180-degree reversal would mean instant self-collision — ignore it
        if len(snake.body) > 1 and direction == OPPOSITE[snake.direction]:
            return
        snake.direction = direction

    # -- tick ----------------------------------------------------------------

    def tick(self):
        if not self.snakes:
            return

        # Compute every snake's next head first, so head-on collisions are symmetric.
        next_heads = {}
        for snake in self.snakes.values():
            dx, dy = DIRS[snake.direction]
            hx, hy = snake.body[0]
            next_heads[snake.id] = (hx + dx, hy + dy)

        # Cells that are lethal to move into: every body cell, except each
        # snake's tail when that tail is about to move out of the way.
        occupied = set()
        for snake in self.snakes.values():
            cells = snake.body if snake.pending_growth > 0 else snake.body[:-1]
            occupied.update(cells)

        dead = set()
        for sid, (nx, ny) in next_heads.items():
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                dead.add(sid)  # wall
            elif (nx, ny) in occupied:
                dead.add(sid)  # body of self or another snake
        # Head-on: two snakes entering the same cell this tick — both die.
        for sid, cell in next_heads.items():
            for other, other_cell in next_heads.items():
                if sid != other and cell == other_cell:
                    dead.add(sid)

        # Move survivors.
        for sid, snake in self.snakes.items():
            if sid in dead:
                continue
            snake.body.insert(0, next_heads[sid])
            if next_heads[sid] in self.food:
                self.food.remove(next_heads[sid])
                snake.score += 1
                snake.pending_growth += 1
            if snake.pending_growth > 0:
                snake.pending_growth -= 1
            else:
                snake.body.pop()

        # Dead snakes respawn immediately so the demo never goes quiet.
        for sid in dead:
            snake = self.snakes[sid]
            head = self._random_free_cell()
            if head is None:
                continue  # board is somehow packed; try again next tick
            snake.body = [head]
            snake.direction = self.rng.choice(list(DIRS))
            snake.pending_growth = START_LEN - 1
            snake.deaths += 1
            snake.score = 0

        self._top_up_food()

    # -- state ---------------------------------------------------------------

    def state(self):
        return {
            "width": self.width,
            "height": self.height,
            "food": [list(cell) for cell in self.food],
            "snakes": {
                sid: {
                    "body": [list(cell) for cell in s.body],
                    "direction": s.direction,
                    "score": s.score,
                    "deaths": s.deaths,
                    "color": s.color_slot,
                }
                for sid, s in self.snakes.items()
            },
        }

    # -- internals -----------------------------------------------------------

    def _blocked_cells(self):
        cells = set(self.food)
        for snake in self.snakes.values():
            cells.update(snake.body)
        return cells

    def _random_free_cell(self):
        blocked = self._blocked_cells()
        free = [
            (x, y)
            for x in range(self.width)
            for y in range(self.height)
            if (x, y) not in blocked
        ]
        return self.rng.choice(free) if free else None

    def _top_up_food(self):
        while len(self.food) < self.food_count:
            cell = self._random_free_cell()
            if cell is None:
                return
            self.food.append(cell)
