# world/loader.py
import random
from core.settings import TILE_SIZE, GRAVITY, JUMP_SPEED


def _single_jump_height_px() -> float:
    # h = v^2 / (2g)
    return (JUMP_SPEED * JUMP_SPEED) / (2.0 * GRAVITY)


def _overlap_len(a0: int, a1: int, b0: int, b1: int) -> int:
    return max(0, min(a1, b1) - max(a0, b0))


def load_demo_level(cols: int = 60, rows: int = 22, seed: int = 1337):
    rng = random.Random(seed)

    # --- Jump-based vertical spacing (tiles) ---
    h1 = _single_jump_height_px()
    min_gap_tiles = max(1, int(round((0.75 * h1) / TILE_SIZE)))
    max_gap_tiles = max(min_gap_tiles, int(round((1.50 * h1) / TILE_SIZE)))

    # --- Grid init ---
    grid = [["." for _ in range(cols)] for _ in range(rows)]

    # Ground (2 tiles thick)
    for y in range(rows - 2, rows):
        for x in range(cols):
            grid[y][x] = "#"

    # Platform params
    platform_min_len = 4
    platform_max_len = 10
    max_overlap_ratio = 0.30  # <= 30% overlap with platform below

    # Track placed platforms by row to prevent same-row overlap
    # stored as (x0, x1) in tile coords
    platforms_by_row = {}

    def row_has_overlap(y: int, x0: int, x1: int) -> bool:
        for a0, a1 in platforms_by_row.get(y, []):
            if _overlap_len(a0, a1, x0, x1) > 0:
                return True
        return False

    def record_platform(y: int, x0: int, x1: int):
        platforms_by_row.setdefault(y, []).append((x0, x1))

    def place_platform(x0: int, y: int, length: int):
        x1 = min(cols - 1, x0 + length)  # exclusive end
        x0 = max(1, x0)
        x1 = max(x0 + 1, x1)

        for x in range(x0, x1):
            grid[y][x] = "#"

        record_platform(y, x0, x1)
        return x0, x1

    # --- First platform near bottom ---
    current_y = rows - 4
    first_len = rng.randint(platform_min_len, platform_max_len)
    current_x0 = rng.randint(2, cols - (first_len + 3))
    current_x1 = current_x0 + first_len

    # Player spawn (above first platform)
    spawn_x = min(cols - 2, current_x0 + 1)
    spawn_y = max(1, current_y - 1)
    grid[spawn_y][spawn_x] = "P"

    # Place first platform
    current_x0, current_x1 = place_platform(current_x0, current_y, first_len)

    # --- Generate upward platforms ---
    safety = 0
    while current_y > 3 and safety < 300:
        safety += 1

        gap_tiles = rng.randint(min_gap_tiles, max_gap_tiles)
        next_y = current_y - gap_tiles
        if next_y < 2:
            break

        length = rng.randint(platform_min_len, platform_max_len)

        # Try multiple candidate x positions until overlap rule satisfied
        best = None
        for _ in range(80):
            candidate_x0 = rng.randint(2, cols - (length + 3))
            candidate_x1 = candidate_x0 + length

            # overlap ratio relative to the platform below
            ov = _overlap_len(candidate_x0, candidate_x1, current_x0, current_x1)
            overlap_ratio = ov / max(1, (current_x1 - current_x0))

            # must be <= 30% overlap with platform below
            if overlap_ratio > max_overlap_ratio:
                continue

            # no same-row overlap with existing platforms
            if row_has_overlap(next_y, candidate_x0, candidate_x1):
                continue

            best = (candidate_x0, candidate_x1)
            break

        # Fallback: if we failed to find a good one, force a far-shift placement
        if best is None:
            # push platform away from below platform center
            below_center = (current_x0 + current_x1) // 2
            if below_center < cols // 2:
                candidate_x0 = rng.randint(cols // 2, cols - (length + 3))
            else:
                candidate_x0 = rng.randint(2, max(3, cols // 2 - (length + 2)))
            candidate_x1 = candidate_x0 + length

            # ensure no same-row overlap; if overlap, slide until clear
            tries = 0
            while row_has_overlap(next_y, candidate_x0, candidate_x1) and tries < 50:
                candidate_x0 = max(2, min(cols - (length + 3), candidate_x0 + rng.choice([-2, 2, -3, 3])))
                candidate_x1 = candidate_x0 + length
                tries += 1

            best = (candidate_x0, candidate_x1)

        next_x0, next_x1 = best
        placed_x0, placed_x1 = place_platform(next_x0, next_y, length)

        # Optional bonus platform (kept rare, and never overlaps on its row)
        if rng.random() < 0.22:
            bonus_len = rng.randint(3, 6)
            bonus_y = max(2, min(rows - 4, next_y + rng.randint(-1, 1)))

            for _ in range(40):
                bx0 = rng.randint(2, cols - (bonus_len + 3))
                bx1 = bx0 + bonus_len
                if not row_has_overlap(bonus_y, bx0, bx1):
                    place_platform(bx0, bonus_y, bonus_len)
                    break

        current_x0, current_x1 = placed_x0, placed_x1
        current_y = next_y

    return ["".join(row) for row in grid]