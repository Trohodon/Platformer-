# world/pathfield.py
import pygame
from collections import deque
from core.settings import TILE_SIZE

SOLID_CHARS = {"#", "C", "M"}


class FlowField:
    """
    Fast crowd pathing:
    - Build a distance field from a target (usually player tile)
    - Enemies read neighbor distances to choose a direction (no per-enemy A*)
    - Rebuild only occasionally (e.g., 4–8 times/sec)

    Works best for "many enemies chase player" maps.
    """

    def __init__(self, grid):
        self.grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0]) if self.rows else 0

        self.dist = None           # 2D list of ints
        self.target_tile = None    # (tx, ty)
        self.valid = False

    def rebuild(self, target_world_pos: pygame.Vector2):
        if self.rows == 0 or self.cols == 0:
            self.valid = False
            return

        tx = int(target_world_pos.x // TILE_SIZE)
        ty = int(target_world_pos.y // TILE_SIZE)
        tx = max(0, min(self.cols - 1, tx))
        ty = max(0, min(self.rows - 1, ty))

        # If target is inside a wall, find nearest walkable
        if self._is_blocked(tx, ty):
            found = self._find_nearest_open(tx, ty, radius=8)
            if found is None:
                self.valid = False
                return
            tx, ty = found

        self.target_tile = (tx, ty)
        self.dist = [[-1] * self.cols for _ in range(self.rows)]

        q = deque()
        self.dist[ty][tx] = 0
        q.append((tx, ty))

        while q:
            x, y = q.popleft()
            d = self.dist[y][x]

            # 4-neighborhood (simple, fast)
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < self.cols and 0 <= ny < self.rows:
                    if self.dist[ny][nx] != -1:
                        continue
                    if self._is_blocked(nx, ny):
                        continue
                    self.dist[ny][nx] = d + 1
                    q.append((nx, ny))

        self.valid = True

    def direction_at_world(self, world_pos: pygame.Vector2) -> pygame.Vector2:
        """
        Returns a unit-ish vector pointing "downhill" in the distance field.
        If invalid/unreachable, returns (0,0).
        """
        if not self.valid or self.dist is None:
            return pygame.Vector2(0, 0)

        x = int(world_pos.x // TILE_SIZE)
        y = int(world_pos.y // TILE_SIZE)

        if not (0 <= x < self.cols and 0 <= y < self.rows):
            return pygame.Vector2(0, 0)

        cur = self.dist[y][x]
        if cur < 0:
            return pygame.Vector2(0, 0)

        best = cur
        best_dir = pygame.Vector2(0, 0)

        # Prefer 4-neighbors (more stable); allow diagonals as tie-breaker
        neighbors = [
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (1, -1), (-1, 1), (-1, -1)
        ]

        for dx, dy in neighbors:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.cols and 0 <= ny < self.rows:
                nd = self.dist[ny][nx]
                if nd >= 0 and nd < best:
                    best = nd
                    best_dir = pygame.Vector2(dx, dy)

        if best_dir.length_squared() == 0:
            return pygame.Vector2(0, 0)

        return best_dir.normalize()

    def _is_blocked(self, x: int, y: int) -> bool:
        ch = self.grid[y][x]
        return ch in SOLID_CHARS

    def _find_nearest_open(self, x: int, y: int, radius: int = 8):
        for r in range(1, radius + 1):
            for oy in range(-r, r + 1):
                for ox in range(-r, r + 1):
                    nx, ny = x + ox, y + oy
                    if 0 <= nx < self.cols and 0 <= ny < self.rows:
                        if not self._is_blocked(nx, ny):
                            return (nx, ny)
        return None