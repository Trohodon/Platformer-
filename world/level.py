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
        self.world_rect = self._compute_world_rect()

        spawn = self._find_player_spawn()
        self.player = Player(spawn.x, spawn.y)

        self.respawn_point = pygame.Vector2(spawn)
        self.fall_y = self.world_rect.bottom + TILE_SIZE * 6

    def _compute_world_rect(self) -> pygame.Rect:
        rows = len(self.grid)
        cols = len(self.grid[0]) if rows else 0
        return pygame.Rect(0, 0, cols * TILE_SIZE, rows * TILE_SIZE)

    def _find_player_spawn(self) -> pygame.Vector2:
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch == "P":
                    return pygame.Vector2(x * TILE_SIZE + 8, y * TILE_SIZE + 2)
        return pygame.Vector2(TILE_SIZE * 2, TILE_SIZE * 2)

    def update(self, dt, input_state, jump_pressed, jump_released, jump_held, dash_pressed):
        solids = self.tilemap.get_solid_rects_near(self.player.rect)

        self.player.update(
            dt,
            input_state,
            jump_pressed=jump_pressed,
            jump_released=jump_released,
            jump_held=jump_held,
            dash_pressed=dash_pressed,
            solids=solids
        )

        # clamp to world horizontally
        self.player.rect.left = max(self.world_rect.left, self.player.rect.left)
        self.player.rect.right = min(self.world_rect.right, self.player.rect.right)

        # checkpoint when grounded
        if self.player.on_ground:
            self.respawn_point.update(self.player.rect.topleft)

        # spikes = damage (30 per hit)
        for spike in self.tilemap.spikes:
            if self.player.rect.colliderect(spike):
                self.player.take_damage(30)
                break

        # death condition (0 HP) => respawn + full heal
        if self.player.health <= 0:
            self._respawn(full_heal=True)

        # fall off world => respawn (no heal unless you want it)
        if self.player.rect.top > self.fall_y:
            self._respawn(full_heal=False)

    def _respawn(self, full_heal: bool):
        self.player.rect.topleft = self.respawn_point
        self.player.vel.xy = (0, 0)
        if full_heal:
            self.player.health = self.player.max_health
            self.player.hurt_timer = 0.0  # clear i-frames on respawn

    def draw(self, surf, camera):
        self.tilemap.draw(surf, camera)
        self.player.draw(surf, camera)