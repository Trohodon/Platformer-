# world/level.py
import pygame

from core.settings import TILE_SIZE
from world.loader import load_demo_level
from world.tilemap import Tilemap
from entities.player import Player


class Level:
    def __init__(self):
        self.grid = load_demo_level()
        self.tilemap = Tilemap(self.grid)

        # Spawn + player
        spawn = self._find_player_spawn()
        self.player = Player(spawn.x, spawn.y)

        # Simple "spice": parallax background stars + world bounds
        self._stars = self._make_stars(seed=1337, count=140)
        self.world_rect = self._compute_world_rect()

        # Optional: respawn if you fall off the world
        self.respawn_point = pygame.Vector2(spawn.x, spawn.y)
        self.fall_y = self.world_rect.bottom + TILE_SIZE * 6

    def _compute_world_rect(self) -> pygame.Rect:
        rows = len(self.grid)
        cols = len(self.grid[0]) if rows else 0
        return pygame.Rect(0, 0, cols * TILE_SIZE, rows * TILE_SIZE)

    def _make_stars(self, seed: int, count: int):
        rng = pygame.math.Vector2(seed, seed * 2)
        stars = []
        # Deterministic-ish pseudo random without importing random
        x = 1234567 + seed * 97
        y = 7654321 + seed * 53
        for i in range(count):
            x = (1103515245 * x + 12345) & 0x7FFFFFFF
            y = (1664525 * y + 1013904223) & 0x7FFFFFFF
            sx = x % max(1, self.world_rect.width)
            sy = y % max(1, self.world_rect.height)
            size = 1 + (x % 2)
            layer = 0.25 + ((y % 75) / 100.0)  # 0.25..0.99
            stars.append((sx, sy, size, layer))
        return stars

    def _find_player_spawn(self) -> pygame.Vector2:
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch == "P":
                    # Slight offset so the player isn't perfectly aligned with tile edges
                    return pygame.Vector2(x * TILE_SIZE + 8, y * TILE_SIZE + 2)
        return pygame.Vector2(TILE_SIZE * 2, TILE_SIZE * 2)

    def update(self, dt: float, input_state, jump_pressed: bool, jump_released: bool, jump_held: bool):
        solids = self.tilemap.get_solid_rects_near(self.player.rect)
        self.player.update(dt, input_state, jump_pressed, jump_released, jump_held, solids)

        # "Spice": keep player within horizontal world bounds
        if self.player.rect.left < self.world_rect.left:
            self.player.rect.left = self.world_rect.left
        if self.player.rect.right > self.world_rect.right:
            self.player.rect.right = self.world_rect.right

        # Respawn if the player falls too far
        if self.player.rect.top > self.fall_y:
            self._respawn()

        # Update respawn point when standing on solid ground (feels like checkpoints)
        if self.player.on_ground:
            self.respawn_point.x = self.player.rect.x
            self.respawn_point.y = self.player.rect.y

    def _respawn(self):
        self.player.rect.x = int(self.respawn_point.x)
        self.player.rect.y = int(self.respawn_point.y)
        self.player.vel.x = 0
        self.player.vel.y = 0

    def draw(self, surf: pygame.Surface, camera):
        # Parallax starfield
        camx, camy = camera.pos.x, camera.pos.y
        for sx, sy, size, layer in self._stars:
            px = sx - int(camx * layer)
            py = sy - int(camy * layer)
            # Wrap stars to avoid popping
            px %= max(1, self.world_rect.width)
            py %= max(1, self.world_rect.height)

            # Only draw if on screen-ish (cheap cull)
            if -10 <= px - camx <= surf.get_width() + 10 and -10 <= py - camy <= surf.get_height() + 10:
                screen_x = int(px - camx)
                screen_y = int(py - camy)
                pygame.draw.rect(surf, (120, 120, 160), (screen_x, screen_y, size, size))

        # World tiles + player
        self.tilemap.draw(surf, camera)
        self.player.draw(surf, camera)

        # Debug-ish "spice": world border
        border = pygame.Rect(self.world_rect)
        pygame.draw.rect(surf, (45, 45, 60), camera.apply(border), 2)