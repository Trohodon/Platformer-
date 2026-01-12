# world/tilemap.py
import pygame
from core.settings import TILE_SIZE, TILE_COLOR

SOLID_CHARS = {"#", "C", "M"}

class Tilemap:
    def __init__(self, grid):
        self.grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0]) if self.rows else 0

        self.solids = []  # list[pygame.Rect]
        self.spikes = []  # list[pygame.Rect]
        self._build()

    def _build(self):
        self.solids.clear()
        self.spikes.clear()

        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                r = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

                if ch in SOLID_CHARS:
                    self.solids.append(r)

                elif ch == "^":
                    # spikes are hazards (smaller rect looks nicer)
                    spike = pygame.Rect(
                        r.x + TILE_SIZE // 6,
                        r.y + TILE_SIZE // 3,
                        TILE_SIZE * 2 // 3,
                        TILE_SIZE * 2 // 3
                    )
                    self.spikes.append(spike)

    def draw(self, surf: pygame.Surface, camera):
        # Solids
        for r in self.solids:
            pygame.draw.rect(surf, TILE_COLOR, camera.apply(r))

        # Spikes (hazards)
        for s in self.spikes:
            pygame.draw.rect(surf, (200, 70, 70), camera.apply(s))

    def get_solid_rects_near(self, rect: pygame.Rect):
        # later you can optimize; for now keep simple
        return self.solids