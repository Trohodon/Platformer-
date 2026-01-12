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

        # World bounds FIRST (fixes your crash)
        self.world_rect = self._compute_world_rect()

        # Player
        spawn = self._find_player_spawn()
        self.player = Player(spawn.x, spawn.y)

        # Respawn / checkpoint
        self.respawn_point = pygame.Vector2(spawn)
        self.fall_y = self.world_rect.bottom + TILE_SIZE * 6

        # Parallax background
        self.stars = self._make_stars(seed=1337, count=160)

        # Screen shake (simple but effective)
        self.shake_timer = 0.0
        self.shake_strength = 0.0

    # -------------------------------------------------

    def _compute_world_rect(self) -> pygame.Rect:
        rows = len(self.grid)
        cols = len(self.grid[0]) if rows else 0
        return pygame.Rect(0, 0, cols * TILE_SIZE, rows * TILE_SIZE)

    def _find_player_spawn(self) -> pygame.Vector2:
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch == "P":
                    return pygame.Vector2(
                        x * TILE_SIZE + 8,
                        y * TILE_SIZE + 2
                    )
        return pygame.Vector2(TILE_SIZE * 2, TILE_SIZE * 2)

    def _make_stars(self, seed: int, count: int):
        stars = []

        x = 1234567 + seed * 97
        y = 7654321 + seed * 53

        for _ in range(count):
            x = (1103515245 * x + 12345) & 0x7FFFFFFF
            y = (1664525 * y + 1013904223) & 0x7FFFFFFF

            sx = x % max(1, self.world_rect.width)
            sy = y % max(1, self.world_rect.height)

            size = 1 + (x & 1)
            layer = 0.2 + ((y % 80) / 100.0)  # depth factor

            stars.append((sx, sy, size, layer))

        return stars

    # -------------------------------------------------

    def update(self, dt, input_state, jump_pressed, jump_released, jump_held):
        solids = self.tilemap.get_solid_rects_near(self.player.rect)
        self.player.update(
            dt,
            input_state,
            jump_pressed,
            jump_released,
            jump_held,
            solids
        )

        # Horizontal world clamp
        self.player.rect.left = max(self.world_rect.left, self.player.rect.left)
        self.player.rect.right = min(self.world_rect.right, self.player.rect.right)

        # Update checkpoint when grounded
        if self.player.on_ground:
            self.respawn_point.update(self.player.rect.topleft)

        # Fell off world → respawn
        if self.player.rect.top > self.fall_y:
            self._respawn()

        # Screen shake decay
        if self.shake_timer > 0:
            self.shake_timer -= dt
            if self.shake_timer <= 0:
                self.shake_strength = 0

    def _respawn(self):
        self.player.rect.topleft = self.respawn_point
        self.player.vel.xy = (0, 0)

        # Trigger shake
        self.shake_timer = 0.18
        self.shake_strength = 6

    # -------------------------------------------------

    def draw(self, surf, camera):
        # Screen shake offset
        shake_x = shake_y = 0
        if self.shake_timer > 0:
            shake_x = int((pygame.time.get_ticks() % 3 - 1) * self.shake_strength)
            shake_y = int((pygame.time.get_ticks() % 5 - 2) * self.shake_strength)

        camx = camera.pos.x + shake_x
        camy = camera.pos.y + shake_y

        # Parallax stars
        for sx, sy, size, layer in self.stars:
            px = sx - int(camx * layer)
            py = sy - int(camy * layer)

            screen_x = int(px - camx)
            screen_y = int(py - camy)

            if -4 <= screen_x <= surf.get_width() + 4 and -4 <= screen_y <= surf.get_height() + 4:
                pygame.draw.rect(
                    surf,
                    (120, 120, 160),
                    (screen_x, screen_y, size, size)
                )

        # World + player
        self.tilemap.draw(surf, camera)
        self.player.draw(surf, camera)

        # World boundary (debug polish)
        pygame.draw.rect(
            surf,
            (45, 45, 60),
            camera.apply(self.world_rect),
            2
        )