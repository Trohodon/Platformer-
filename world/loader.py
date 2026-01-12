# world/loader.py
import random
from collections import deque

from core.settings import TILE_SIZE, GRAVITY, JUMP_SPEED, MOVE_SPEED


# Tile legend:
# '.' empty
# '#' solid
# 'P' player spawn (treated as empty)
# '^' spikes (hazard)
# 'C' crumble (solid for now; can be expanded later)
# 'M' moving platform (solid for now; can be expanded later)


def _single_jump_height_px() -> float:
    return (JUMP_SPEED * JUMP_SPEED) / (2.0 * GRAVITY)


def _time_to_apex() -> float:
    return JUMP_SPEED / GRAVITY


def _rng_seed(seed):
    return seed if seed is not None else random.randrange(1, 2_000_000_000)


def _is_solid(ch: str) -> bool:
    return ch in ("#", "C", "M")


def _is_empty(ch: str) -> bool:
    return ch in (".", "P", "^")


def _place_rect_solid(grid, x0, y0, w, h, ch="#"):
    rows = len(grid)
    cols = len(grid[0])
    for y in range(y0, y0 + h):
        if not (0 <= y < rows):
            continue
        for x in range(x0, x0 + w):
            if 0 <= x < cols:
                grid[y][x] = ch


def _carve_rect_empty(grid, x0, y0, w, h):
    rows = len(grid)
    cols = len(grid[0])
    for y in range(y0, y0 + h):
        if not (0 <= y < rows):
            continue
        for x in range(x0, x0 + w):
            if 0 <= x < cols:
                grid[y][x] = "."


def _place_platform(grid, x0, y, length, ch="#"):
    cols = len(grid[0])
    x0 = max(1, min(cols - 2, x0))
    x1 = max(x0 + 2, min(cols - 1, x0 + length))  # exclusive
    for x in range(x0, x1):
        grid[y][x] = ch
    return x0, x1


def _top_surface_cells(grid):
    rows = len(grid)
    cols = len(grid[0])
    tops = []
    for y in range(1, rows):
        for x in range(cols):
            if _is_solid(grid[y][x]) and _is_empty(grid[y - 1][x]):
                tops.append((x, y - 1))
    return tops


def _reachable_validator(grid, spawn_xy, goal_y_max, min_gap_tiles, max_gap_tiles,
                         max_dx_single, max_dx_double, approx_single_h_tiles):
    rows = len(grid)
    tops = _top_surface_cells(grid)
    if not tops:
        return False

    tops_by_y = {}
    for x, y in tops:
        tops_by_y.setdefault(y, []).append(x)

    sx, sy = spawn_xy

    start = None
    best_d = 10**9
    for x, y in tops:
        d = abs(x - sx) + abs(y - sy)
        if d < best_d:
            best_d = d
            start = (x, y)

    if start is None:
        return False

    q = deque([start])
    visited = set([start])

    def neighbors(ax, ay):
        for by in range(max(1, ay - (max_gap_tiles + 2)), min(rows - 1, ay + 6)):
            if by not in tops_by_y:
                continue

            dy = ay - by  # + means target higher
            needs_double = dy > approx_single_h_tiles
            max_dx = max_dx_double if needs_double else max_dx_single

            if dy > 0:
                if dy < int(0.70 * min_gap_tiles) or dy > int(1.20 * max_gap_tiles):
                    continue
            else:
                if abs(dy) > 5:
                    continue

            for bx in tops_by_y[by]:
                if abs(bx - ax) <= max_dx:
                    yield (bx, by)

    while q:
        ax, ay = q.popleft()
        if ay <= goal_y_max:
            return True
        for nb in neighbors(ax, ay):
            if nb not in visited:
                visited.add(nb)
                q.append(nb)

    return False


def load_demo_level(cols: int = 80, rows: int = 26, seed=None):
    h1 = _single_jump_height_px()
    min_gap_tiles = max(1, int(round((0.75 * h1) / TILE_SIZE)))
    max_gap_tiles = max(min_gap_tiles, int(round((1.50 * h1) / TILE_SIZE)))
    approx_single_h_tiles = max(1, int(round(h1 / TILE_SIZE)))

    t_apex = _time_to_apex()
    single_air = 2.0 * t_apex
    double_air = 4.0 * t_apex
    max_dx_single = max(3, int((MOVE_SPEED * single_air) / TILE_SIZE))
    max_dx_double = max(max_dx_single + 2, int((MOVE_SPEED * double_air) / TILE_SIZE))

    biomes = [
        ("ruins",   (4, 6),  (25, 40), 0.06, 0.55, 1.0),
        ("cavern",  (3, 5),  (35, 55), 0.08, 0.35, 1.2),
        ("tower",   (5, 8),  (20, 35), 0.05, 0.75, 0.9),
        ("chaos",   (6, 9),  (45, 75), 0.10, 0.60, 1.4),
    ]

    base_seed = _rng_seed(seed)

    for attempt in range(60):
        rng = random.Random(base_seed + attempt * 99991)
        _, room_range, extra_range, spike_density, wall_density, intensity = rng.choice(biomes)

        grid = [["." for _ in range(cols)] for _ in range(rows)]

        for y in range(rows):
            grid[y][0] = "#"
            grid[y][cols - 1] = "#"

        for y in range(rows - 2, rows):
            for x in range(cols):
                grid[y][x] = "#"

        # -------- Rooms --------
        room_count = rng.randint(*room_range)
        rooms = []
        for _ in range(room_count):
            w = rng.randint(14, 22)
            h = rng.randint(8, 12)
            x0 = rng.randint(2, cols - w - 2)
            y0 = rng.randint(2, rows - h - 4)

            _place_rect_solid(grid, x0, y0, w, h, "#")
            _carve_rect_empty(grid, x0 + 1, y0 + 1, w - 2, h - 2)
            rooms.append((x0, y0, w, h))

            floor_y = y0 + h - 2
            plat_len = rng.randint(max(6, w - 10), w - 2)
            plat_x = x0 + rng.randint(1, max(1, (w - plat_len - 1)))
            _place_platform(grid, plat_x, floor_y, plat_len, "#")

        # -------- Doors between rooms (FIXED) --------
        for i in range(len(rooms) - 1):
            x0, y0, w0, h0 = rooms[i]
            x1, y1, w1, h1r = rooms[i + 1]

            lo = max(y0 + 2, y1 + 2)
            hi = min(y0 + h0 - 3, y1 + h1r - 3)

            # If there is no valid overlap band, skip making a door between these rooms.
            if lo > hi:
                continue

            door_y = rng.randint(lo, hi)

            ax = x0 + w0 - 1
            bx = x1
            if ax > bx:
                ax, bx = bx, ax

            for x in range(ax, bx + 1):
                if 1 <= x <= cols - 2 and 1 <= door_y <= rows - 3:
                    grid[door_y][x] = "."
                    grid[door_y - 1][x] = "."
                    grid[door_y + 1][x] = "."

        # -------- Main platform path --------
        platform_min_len = 4
        platform_max_len = int(12 * intensity)

        current_y = rows - 4
        length = rng.randint(8, max(8, platform_max_len))
        current_x0 = rng.randint(3, cols - (length + 4))
        current_x0, current_x1 = _place_platform(grid, current_x0, current_y, length, "#")

        spawn_x = min(cols - 3, current_x0 + 2)
        spawn_y = max(1, current_y - 1)
        grid[spawn_y][spawn_x] = "P"

        main_path = [(current_y, current_x0, current_x1)]
        safety = 0
        max_overlap_ratio = 0.30

        while current_y > 4 and safety < 500:
            safety += 1
            gap_tiles = rng.randint(min_gap_tiles, max_gap_tiles)
            next_y = current_y - gap_tiles
            if next_y < 2:
                break

            length = rng.randint(platform_min_len, max(6, platform_max_len))
            below_center = (current_x0 + current_x1) // 2
            needs_double = gap_tiles > approx_single_h_tiles
            max_dx = max_dx_double if needs_double else max_dx_single

            best = None
            for _ in range(160):
                dx = rng.randint(-max_dx, max_dx)
                cand_center = below_center + dx
                cand_x0 = cand_center - length // 2
                cand_x0 = max(2, min(cols - (length + 3), cand_x0))
                cand_x1 = cand_x0 + length

                ov = max(0, min(cand_x1, current_x1) - max(cand_x0, current_x0))
                overlap_ratio = ov / max(1, (current_x1 - current_x0))
                if overlap_ratio > max_overlap_ratio:
                    continue

                best = (cand_x0, cand_x1)
                break

            if best is None:
                if below_center < cols // 2:
                    cand_x0 = rng.randint(cols // 2, cols - (length + 3))
                else:
                    cand_x0 = rng.randint(2, max(3, cols // 2 - (length + 2)))
                cand_x1 = cand_x0 + length
                best = (cand_x0, cand_x1)

            next_x0, next_x1 = best
            placed_x0, placed_x1 = _place_platform(grid, next_x0, next_y, length, "#")
            main_path.append((next_y, placed_x0, placed_x1))

            current_y, current_x0, current_x1 = next_y, placed_x0, placed_x1

        # -------- Extra platforms --------
        extra_count = rng.randint(*extra_range)
        for _ in range(extra_count):
            y = rng.randint(2, rows - 6)
            length = rng.randint(3, int(10 * intensity))
            x0 = rng.randint(2, cols - (length + 3))
            r = rng.random()
            ch = "C" if r < 0.10 else "M" if r < 0.16 else "#"
            _place_platform(grid, x0, y, length, ch)

        # -------- Walls/columns --------
        col_count = rng.randint(int(6 * wall_density), int(14 * wall_density + 2))
        for _ in range(col_count):
            x = rng.randint(4, cols - 5)
            y0 = rng.randint(2, rows // 2)
            y1 = rng.randint(rows // 2, rows - 4)

            gap_y = None
            if main_path and rng.random() < 0.9:
                py, _, _ = rng.choice(main_path)
                gap_y = max(2, min(rows - 7, py - rng.randint(0, 2)))
            gap_h = rng.randint(3, 5)

            for y in range(y0, y1 + 1):
                if gap_y is not None and gap_y <= y < gap_y + gap_h:
                    continue
                grid[y][x] = "#"

            if rng.random() < 0.35:
                xx = x + rng.choice([-1, 1])
                if 2 <= xx <= cols - 3:
                    for y in range(y0, y1 + 1):
                        if gap_y is not None and gap_y <= y < gap_y + gap_h:
                            continue
                        grid[y][xx] = "#"

        # -------- Spikes --------
        # Put spikes above solids, avoid spawn neighborhood
        for y in range(2, rows - 3):
            for x in range(2, cols - 2):
                if (x - spawn_x) ** 2 + (y - spawn_y) ** 2 < 25:
                    continue
                if _is_solid(grid[y][x]) and _is_empty(grid[y - 1][x]) and rng.random() < spike_density:
                    grid[y - 1][x] = "^"

        ok = _reachable_validator(
            grid=grid,
            spawn_xy=(spawn_x, spawn_y),
            goal_y_max=4,
            min_gap_tiles=min_gap_tiles,
            max_gap_tiles=max_gap_tiles,
            max_dx_single=max_dx_single,
            max_dx_double=max_dx_double,
            approx_single_h_tiles=approx_single_h_tiles,
        )

        if ok:
            return ["".join(row) for row in grid]

    # fallback
    fallback = [["." for _ in range(cols)] for _ in range(rows)]
    for y in range(rows - 2, rows):
        for x in range(cols):
            fallback[y][x] = "#"
    fallback[rows - 5][4] = "P"
    for i in range(5, cols - 5, 8):
        _place_platform(fallback, i, rows - 8, 6, "#")
    return ["".join(r) for r in fallback]