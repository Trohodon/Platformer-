# world/level.py
import pygame
from core.settings import TILE_SIZE
from world.loader import load_demo_level
from world.tilemap import Tilemap
from entities.player import Player
from entities.enemy import Enemy


class Level:
    def __init__(self):
        self.grid = load_demo_level()
        self.tilemap = Tilemap(self.grid)
        self.world_rect = self._compute_world_rect()

        spawn = self._find_player_spawn()
        self.player = Player(spawn.x, spawn.y)

        self.respawn_point = pygame.Vector2(spawn)
        self.fall_y = self.world_rect.bottom + TILE_SIZE * 6

        # Enemies + bullets
        self.enemies: list[Enemy] = []
        self.bullets = []  # list[Bullet]

        self._spawn_enemies()

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

    def _spawn_enemies(self):
        # spawn enemies on valid "standable" spots (empty above solid)
        candidates = []
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch in ("#", "C", "M") and y > 0:
                    above = self.grid[y - 1][x]
                    if above in (".", "^", "P"):
                        wx = x * TILE_SIZE + TILE_SIZE // 2
                        wy = (y - 1) * TILE_SIZE + TILE_SIZE // 2
                        candidates.append((wx, wy))

        # pick some, but keep them away from spawn
        sx, sy = self.player.rect.centerx, self.player.rect.centery
        candidates = [c for c in candidates if (c[0] - sx) ** 2 + (c[1] - sy) ** 2 > (TILE_SIZE * 8) ** 2]

        # cap enemy count for performance
        count = min(18, max(6, len(candidates) // 30))
        for i in range(count):
            if not candidates:
                break
            x, y = candidates.pop(i % len(candidates))
            self.enemies.append(Enemy(x, y, radius=16))

    def update(self, dt, input_state, jump_pressed, jump_released, jump_held, dash_pressed, shoot_pressed):
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

        # shoot -> spawn bullet
        if shoot_pressed:
            b = self.player.try_shoot()
            if b is not None:
                self.bullets.append(b)

        # clamp player in world
        self.player.rect.left = max(self.world_rect.left, self.player.rect.left)
        self.player.rect.right = min(self.world_rect.right, self.player.rect.right)

        # checkpoint when grounded
        if self.player.on_ground:
            self.respawn_point.update(self.player.rect.topleft)

        # spikes = damage (30/hit)
        for spike in self.tilemap.spikes:
            if self.player.rect.colliderect(spike):
                self.player.take_damage(30)
                break

        # update bullets
        for b in self.bullets:
            b.update(dt, solids)

        # bullet vs enemy
        for b in self.bullets:
            if not b.alive:
                continue
            br = b.rect
            for e in self.enemies:
                if e.dead:
                    continue
                if br.colliderect(e.rect):
                    e.take_damage(b.damage)
                    b.alive = False
                    break

        # update enemies
        for e in self.enemies:
            e.update(dt, self.player.rect, solids)

        # cleanup
        self.bullets = [b for b in self.bullets if b.alive]
        self.enemies = [e for e in self.enemies if not e.dead]

        # death => respawn + heal
        if self.player.health <= 0:
            self._respawn(full_heal=True)

        # fall => respawn (no heal)
        if self.player.rect.top > self.fall_y:
            self._respawn(full_heal=False)

    def _respawn(self, full_heal: bool):
        self.player.rect.topleft = self.respawn_point
        self.player.vel.xy = (0, 0)
        if full_heal:
            self.player.health = self.player.max_health
            self.player.hurt_timer = 0.0

    def draw(self, surf, camera):
        self.tilemap.draw(surf, camera)

        # bullets
        for b in self.bullets:
            b.draw(surf, camera)

        # enemies
        for e in self.enemies:
            e.draw(surf, camera)

        self.player.draw(surf, camera)