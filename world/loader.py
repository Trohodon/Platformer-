# world/loader.py
import random
from core.settings import TILE_SIZE, GRAVITY, JUMP_SPEED, MOVE_SPEED


def _single_jump_height_px() -> float:
    # h = v^2 / (2g)
    return (JUMP_SPEED * JUMP_SPEED) / (2.0 * GRAVITY)


def _time_to_apex() -> float:
    # t = v/g
    return JUMP_SPEED / GRAVITY


def _overlap_len(a0: int, a1: int, b0: int, b1: int) -> int:
    return max(0, min(a1, b1) - max(a0, b0))


def load_demo_level(cols: int = 70, rows: int = 24, seed=None):
    """
    Complex procedural platformer map (Python-only):
    - Main path guaranteed reachable
    - Extra random platforms
    - Walls/columns/shafts
    - Different every run unless seed provided
    """
    rng = random.Random(seed)

    # ---------- Jump rules (vertical gaps in tiles) ----------
    h1 = _single_jump_height_px()
    min_gap_tiles = max(1, int(round((0.75 * h1) / TILE_SIZE)))
    max_gap_tiles = max(min_gap_tiles, int(round((1.50 * h1) / TILE_SIZE)))

    # ---------- Horizontal reach estimate ----------
    t_apex = _time_to_apex()
    single_air_time = 2.0 * t_apex
    double_air_time = 4.0 * t_apex  # rough (two jumps)
    max_dx_single_tiles = max(3, int((MOVE_SPEED * single_air_time) / TILE_SIZE))
    max_dx_double_tiles = max(max_dx_single_tiles + 2, int((MOVE_SPEED * double_air_time) / TILE_SIZE))

    # ---------- Grid init ----------
    grid = [["." for _ in range(cols)] for _ in range(rows)]

    # Border walls (keeps camera/world feeling contained)
    for y in range(rows):
        grid[y][0] = "#"
        grid[y][cols - 1] = "#"

    # Ground (2 tiles thick)
    for y in range(rows - 2, rows):
        for x in range(cols):
            grid[y][x] = "#"

    # Track platforms by row to prevent same-row overlap
    platforms_by_row = {}  # y -> list[(x0,x1)]

    def row_has_overlap(y: int, x0: int, x1: int) -> bool:
        for a0, a1 in platforms_by_row.get(y, []):
            if _overlap_len(a0, a1, x0, x1) > 0:
                return True
        return False

    def record_platform(y: int, x0: int, x1: int):
        platforms_by_row.setdefault(y, []).append((x0, x1))

    def place_platform(x0: int, y: int, length: int):
        x0 = max(1, min(cols - 2, x0))
        x1 = max(x0 + 2, min(cols - 1, x0 + length))  # exclusive
        for x in range(x0, x1):
            grid[y][x] = "#"
        record_platform(y, x0, x1)
        return x0, x1

    def place_wall_column(x: int, y0: int, y1: int, gap_y=None, gap_h=3):
        """
        Solid vertical wall/column from y0..y1 inclusive, with an optional gap.
        """
        y0 = max(1, y0)
        y1 = min(rows - 3, y1)
        if x <= 0 or x >= cols - 1:
            return

        for y in range(y0, y1 + 1):
            if gap_y is not None and gap_y <= y < gap_y + gap_h:
                continue
            grid[y][x] = "#"

    # ---------- Main path generation ----------
    max_overlap_ratio = 0.30

    platform_min_len = 4
    platform_max_len = 12

    # Start platform near bottom
    current_y = rows - 4
    length = rng.randint(7, 12)
    current_x0 = rng.randint(3, cols - (length + 4))
    current_x1 = current_x0 + length
    current_x0, current_x1 = place_platform(current_x0, current_y, length)

    # Player spawn above the first platform
    spawn_x = min(cols - 3, current_x0 + 2)
    spawn_y = max(1, current_y - 1)
    grid[spawn_y][spawn_x] = "P"

    # Keep a list of main path platforms so we can carve gaps in walls later
    main_path = [(current_y, current_x0, current_x1)]

    safety = 0
    while current_y > 4 and safety < 400:
        safety += 1

        gap_tiles = rng.randint(min_gap_tiles, max_gap_tiles)
        next_y = current_y - gap_tiles
        if next_y < 2:
            break

        length = rng.randint(platform_min_len, platform_max_len)

        # Determine whether this jump might require double jump
        # If gap > ~single jump height in tiles, allow larger horizontal reach.
        approx_single_h_tiles = max(1, int(round(h1 / TILE_SIZE)))
        needs_double = gap_tiles > approx_single_h_tiles
        max_dx = max_dx_double_tiles if needs_double else max_dx_single_tiles

        below_center = (current_x0 + current_x1) // 2

        best = None
        for _ in range(120):
            # pick center within reachable dx
            dx = rng.randint(-max_dx, max_dx)
            cand_center = below_center + dx

            cand_x0 = cand_center - length // 2
            cand_x0 = max(2, min(cols - (length + 3), cand_x0))
            cand_x1 = cand_x0 + length

            # overlap <= 30% relative to below platform
            ov = _overlap_len(cand_x0, cand_x1, current_x0, current_x1)
            overlap_ratio = ov / max(1, (current_x1 - current_x0))
            if overlap_ratio > max_overlap_ratio:
                continue

            # no same-row overlap
            if row_has_overlap(next_y, cand_x0, cand_x1):
                continue

            best = (cand_x0, cand_x1)
            break

        if best is None:
            # force a far placement away from below center
            if below_center < cols // 2:
                cand_x0 = rng.randint(cols // 2, cols - (length + 3))
            else:
                cand_x0 = rng.randint(2, max(3, cols // 2 - (length + 2)))
            cand_x1 = cand_x0 + length
            # slide if overlapping on same row
            tries = 0
            while row_has_overlap(next_y, cand_x0, cand_x1) and tries < 60:
                cand_x0 = max(2, min(cols - (length + 3), cand_x0 + rng.choice([-3, 3, -4, 4])))
                cand_x1 = cand_x0 + length
                tries += 1
            best = (cand_x0, cand_x1)

        next_x0, next_x1 = best
        placed_x0, placed_x1 = place_platform(next_x0, next_y, length)

        main_path.append((next_y, placed_x0, placed_x1))

        current_y = next_y
        current_x0, current_x1 = placed_x0, placed_x1

    # ---------- Add “intense” random extra platforms ----------
    extra_count = rng.randint(20, 38)
    for _ in range(extra_count):
        y = rng.randint(2, rows - 6)
        length = rng.randint(3, 10)
        x0 = rng.randint(2, cols - (length + 3))
        x1 = x0 + length

        if row_has_overlap(y, x0, x1):
            continue

        # Don’t let extras overlap too much with a main-path platform directly below (if any)
        below = None
        for (py, px0, px1) in main_path:
            if py > y:
                continue
            if py < y:
                # find the nearest platform below by y distance
                dy = y - py
                if dy <= max_gap_tiles + 2:
                    below = (px0, px1)
                    break
        if below is not None:
            ov = _overlap_len(x0, x1, below[0], below[1])
            overlap_ratio = ov / max(1, (below[1] - below[0]))
            if overlap_ratio > 0.30:
                continue

        place_platform(x0, y, length)

    # ---------- Add walls / columns / shafts ----------
    # We place columns and carve gaps around main path heights so you don’t get hard-blocked.
    col_count = rng.randint(6, 12)
    for _ in range(col_count):
        x = rng.randint(4, cols - 5)

        # decide wall height range
        y0 = rng.randint(2, rows // 2)
        y1 = rng.randint(rows // 2, rows - 4)

        # choose a gap near a random main path platform (doorway)
        gap_y = None
        if main_path and rng.random() < 0.85:
            py, _, _ = rng.choice(main_path)
            gap_y = max(2, min(rows - 6, py - rng.randint(0, 2)))

        place_wall_column(x, y0, y1, gap_y=gap_y, gap_h=rng.randint(3, 5))

        # sometimes thicken the wall to 2-wide
        if rng.random() < 0.35:
            place_wall_column(x + rng.choice([-1, 1]), y0, y1, gap_y=gap_y, gap_h=rng.randint(3, 5))

    # ---------- Sprinkle a few “ledge blocks” (micro platforms) ----------
    micro = rng.randint(18, 35)
    for _ in range(micro):
        y = rng.randint(2, rows - 6)
        x = rng.randint(2, cols - 3)
        if grid[y][x] == "." and grid[y + 1][x] == ".":  # avoid stacking on solids
            # avoid placing inside border walls
            grid[y][x] = "#"

    return ["".join(r) for r in grid]