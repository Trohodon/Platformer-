# world/loader.py
import random
from core.settings import TILE_SIZE, GRAVITY, JUMP_SPEED

def _single_jump_height_px() -> float:
    # h = v^2 / (2g)
    return (JUMP_SPEED * JUMP_SPEED) / (2.0 * GRAVITY)

def load_demo_level(cols: int = 60, rows: int = 22, seed: int = 1337):
    rng = random.Random(seed)

    # Compute jump heights
    h1 = _single_jump_height_px()
    min_gap_px = 0.75 * h1
    max_gap_px = 1.50 * h1

    min_gap_tiles = max(1, int(round(min_gap_px / TILE_SIZE)))
    max_gap_tiles = max(min_gap_tiles, int(round(max_gap_px / TILE_SIZE)))

    # Start with empty grid
    grid = [["." for _ in range(cols)] for _ in range(rows)]

    # Ground (2-tile thick)
    for y in range(rows - 2, rows):
        for x in range(cols):
            grid[y][x] = "#"

    # Platform generation parameters
    platform_min_len = 4
    platform_max_len = 9

    # First platform location (near bottom, above ground)
    current_y = rows - 4
    current_x = rng.randint(2, cols - 10)

    # Place player spawn on first platform area (above platform)
    grid[current_y - 1][current_x + 1] = "P"

    # Helper: place a platform (1 tile thick)
    def place_platform(x0: int, y: int, length: int):
        x1 = min(cols - 2, x0 + length)
        x0c = max(1, x0)
        for x in range(x0c, x1):
            grid[y][x] = "#"

    # Place the first platform
    first_len = rng.randint(platform_min_len, platform_max_len)
    place_platform(current_x, current_y, first_len)

    # Generate upward platforms until we reach near the top
    safety = 0
    while current_y > 3 and safety < 200:
        safety += 1

        gap_tiles = rng.randint(min_gap_tiles, max_gap_tiles)
        next_y = current_y - gap_tiles
        if next_y < 2:
            break

        length = rng.randint(platform_min_len, platform_max_len)

        # Horizontal shift: keep it reachable by allowing some overlap-ish range
        # (You can tune these numbers later for harder/easier)
        shift = rng.randint(-10, 10)
        next_x = current_x + shift
        next_x = max(2, min(cols - (length + 2), next_x))

        # Place platform
        place_platform(next_x, next_y, length)

        # Occasionally place a second “bonus” platform at similar height
        if rng.random() < 0.25:
            bonus_len = rng.randint(3, 6)
            bonus_x = rng.randint(2, cols - (bonus_len + 2))
            bonus_y = next_y + rng.randint(-1, 1)
            bonus_y = max(2, min(rows - 4, bonus_y))
            place_platform(bonus_x, bonus_y, bonus_len)

        current_x, current_y = next_x, next_y

    # Convert to list[str]
    return ["".join(row) for row in grid]