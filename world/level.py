# world/level.py
import pygame

from world.loader import load_demo_level
from world.tilemap import Tilemap
from entities.player import Player

class Level:
    def __init__(self):
        self.grid = load_demo_level()
        self.tilemap = Tilemap(self.grid)

        spawn = self._find_player_spawn()
        self.player = Player(spawn.x, spawn.y)

    def _find_player_spawn(self) -> pygame.Vector2:
        # Look for 'P' in the grid
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch == "P":
                    # spawn slightly above the tile position
                    return pygame.Vector2(x * 48 + 8, y * 48 + 0)
        return pygame.Vector2(64, 64)

    def update(self, dt: float, input_state, jump_requested: bool):
        solids = self.tilemap.get_solid_rects_near(self.player.rect)
        self.player.update(dt, input_state, jump_requested, solids)

    def draw(self, surf: pygame.Surface, camera):
        self.tilemap.draw(surf, camera)
        self.player.draw(surf, camera)