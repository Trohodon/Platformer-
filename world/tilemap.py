# world/tilemap.py
import pygame
from core.settings import TILE_SIZE, TILE_COLOR

class Tilemap:
    def __init__(self, grid):
        self.grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0]) if self.rows else 0

        self.solids = []  # list[pygame.Rect]
        self._build_solids()

    def _build_solids(self):
        self.solids.clear()
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch == "#":
                    r = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    self.solids.append(r)

    def draw(self, surf: pygame.Surface, camera):
        for r in self.solids:
            pygame.draw.rect(surf, TILE_COLOR, camera.apply(r))

    def get_solid_rects_near(self, rect: pygame.Rect):
        # Simple approach: return all solids.
        # Later we can optimize by checking tiles around the player only.
        return self.solids