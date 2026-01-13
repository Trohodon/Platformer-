# world/loader.py
import random


def load_demo_level(seed: int = None, cols: int = 60, rows: int = 34):
    """
    Generates a connected, pocket-free map:
    - Start solid
    - Carve connected corridors with a random walk
    - Widen corridors a bit
    - Add a guaranteed bottom floor band
    Grid chars:
      '#': solid
      '.': empty
      'P': player spawn
      '^': spikes (non-solid damage)
    """
    rng = random.Random(seed if seed is not None else random.randrange(10**9))

    # --- base solid grid ---
    grid = [["#" for _ in range(cols)] for _ in range(rows)]

    def in_bounds(x, y):
        return 1 <= x < cols - 1 and 1 <= y < rows - 1

    def carve(x, y, r=0):
        # carve a dot, optionally with thickness r
        for yy in range(y - r, y + r + 1):
            for xx in range(x - r, x + r + 1):
                if in_bounds(xx, yy):
                    grid[yy][xx] = "."

    # --- random walk digger (guaranteed connected air) ---
    x = cols // 2
    y = rows // 2
    carve(x, y, r=1)

    steps = cols * rows * 8  # density control
    thickness = 1

    for i in range(steps):
        # occasionally change thickness to form "roomy" spaces (still connected)
        if i % 250 == 0:
            thickness = 1 if rng.random() < 0.75 else 2

        carve(x, y, r=thickness)

        # biased direction choices to create longer corridors
        r = rng.random()
        if r < 0.25:
            dx, dy = (1, 0)
        elif r < 0.50:
            dx, dy = (-1, 0)
        elif r < 0.75:
            dx, dy = (0, 1)
        else:
            dx, dy = (0, -1)

        # occasional momentum (keeps corridors coherent)
        if rng.random() < 0.70:
            x2, y2 = x + dx, y + dy
        else:
            # sideways wiggle
            if dx != 0:
                x2, y2 = x + dx, y + rng.choice([-1, 0, 1])
            else:
                x2, y2 = x + rng.choice([-1, 0, 1]), y + dy

        if in_bounds(x2, y2):
            x, y = x2, y2

    # --- ensure a bottom "ground" with open space above it ---
    ground_y = rows - 3
    for xx in range(1, cols - 1):
        grid[ground_y][xx] = "#"
        grid[ground_y - 1][xx] = "."
        if rng.random() < 0.55:
            grid[ground_y - 2][xx] = "."

    # --- widen pass: open up narrow chokepoints, still connected ---
    for _ in range(2):
        for yy in range(2, rows - 2):
            for xx in range(2, cols - 2):
                if grid[yy][xx] == "#":
                    # if surrounded by air, open it
                    air = 0
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        if grid[yy + dy][xx + dx] == ".":
                            air += 1
                    if air >= 3 and rng.random() < 0.6:
                        grid[yy][xx] = "."

    # --- place player spawn on a safe open tile above solid ---
    spawn = _find_spawn(grid, cols, rows, rng)
    sx, sy = spawn
    grid[sy][sx] = "P"

    # --- sprinkle spikes on solid tops (non-solid damage tiles) ---
    spike_count = int((cols * rows) * 0.008)
    for _ in range(spike_count):
        xx = rng.randrange(2, cols - 2)
        yy = rng.randrange(2, rows - 3)
        # place spike on air tile that has solid directly below (top of a platform)
        if grid[yy][xx] == "." and grid[yy + 1][xx] == "#":
            # don't put spikes right on spawn area
            if abs(xx - sx) + abs(yy - sy) > 10:
                grid[yy][xx] = "^"

    # --- borders solid ---
    for xx in range(cols):
        grid[0][xx] = "#"
        grid[rows - 1][xx] = "#"
    for yy in range(rows):
        grid[yy][0] = "#"
        grid[yy][cols - 1] = "#"

    # return as list[str]
    return ["".join(r) for r in grid]


def _find_spawn(grid, cols, rows, rng):
    # try multiple times to find air with solid under it
    for _ in range(5000):
        x = rng.randrange(2, cols - 2)
        y = rng.randrange(2, rows - 4)
        if grid[y][x] == "." and grid[y + 1][x] == "#":
            # make sure a small area is open
            ok = True
            for yy in range(y - 1, y + 2):
                for xx in range(x - 1, x + 2):
                    if grid[yy][xx] == "#":
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                return x, y
    # fallback
    return cols // 2, rows // 2