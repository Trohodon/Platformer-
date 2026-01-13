# world/level.py
import pygame
import random

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

        # bullets / enemies
        self.enemies = []
        self.bullets = []

        # -------- Waves --------
        self.wave_index = 0
        self.wave_active = False
        self.wave_cooldown = 1.2   # delay between waves
        self.wave_timer = 0.6

        # Precompute enemy spawn candidates from this map
        self.spawn_points = self._build_enemy_spawn_points()

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

    def _build_enemy_spawn_points(self):
        points = []
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch in ("#", "C", "M") and y > 0:
                    above = self.grid[y - 1][x]
                    if above in (".", "^", "P"):
                        wx = x * TILE_SIZE + TILE_SIZE // 2
                        wy = (y - 1) * TILE_SIZE + TILE_SIZE // 2
                        points.append((wx, wy))

        # keep points away from player spawn
        sx, sy = self.player.rect.centerx, self.player.rect.centery
        min_d2 = (TILE_SIZE * 10) ** 2
        points = [p for p in points if (p[0] - sx) ** 2 + (p[1] - sy) ** 2 > min_d2]

        # prefer "lower" spawns so waves rise at player
        points.sort(key=lambda p: p[1], reverse=True)
        return points

    def _start_next_wave(self):
        self.wave_index += 1
        self.wave_active = True

        # scale enemy count by wave, with a cap
        base = 6
        add = min(18, self.wave_index * 2)
        count = min(28, base + add)

        # choose spawn points clustered in a couple areas to feel like "waves"
        rng = random.Random(self.wave_index * 99173)
        points = self.spawn_points[:]
        if not points:
            return

        # pick 2-3 "spawn hubs"
        hubs = [points[rng.randrange(0, min(len(points), 60))] for _ in range(rng.randint(2, 3))]

        def pick_point():
            hx, hy = hubs[rng.randrange(len(hubs))]
            # pick a point near hub by index proximity (since sorted by y)
            idx = rng.randrange(0, len(points))
            px, py = points[idx]
            # nudge toward hub a bit
            px = int((px + hx) * 0.5)
            py = int((py + hy) * 0.5)
            return px, py

        self.enemies.clear()
        for i in range(count):
            ex, ey = pick_point()
            self.enemies.append(Enemy(ex, ey, radius=16))

    def update(self, dt, input_state, jump_pressed, jump_released, jump_held, dash_pressed, shoot_pressed):
        solids = self.tilemap.get_solid_rects_near(self.player.rect)

        # ---------------- Player ----------------
        self.player.update(
            dt,
            input_state,
            jump_pressed=jump_pressed,
            jump_released=jump_released,
            jump_held=jump_held,
            dash_pressed=dash_pressed,
            solids=solids
        )

        # shoot
        if shoot_pressed:
            b = self.player.try_shoot()
            if b is not None:
                self.bullets.append(b)

        # clamp player horizontally
        self.player.rect.left = max(self.world_rect.left, self.player.rect.left)
        self.player.rect.right = min(self.world_rect.right, self.player.rect.right)

        # checkpoint when grounded
        if self.player.on_ground:
            self.respawn_point.update(self.player.rect.topleft)

        # spikes damage
        for spike in self.tilemap.spikes:
            if self.player.rect.colliderect(spike):
                self.player.take_damage(30)
                break

        # ---------------- Waves ----------------
        if not self.wave_active:
            self.wave_timer -= dt
            if self.wave_timer <= 0.0:
                self._start_next_wave()
        else:
            # if all enemies dead -> end wave + delay
            living = [e for e in self.enemies if not e.dead]
            if len(living) == 0:
                self.wave_active = False
                self.wave_timer = self.wave_cooldown
                self.enemies.clear()

        # ---------------- Bullets ----------------
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

        # ---------------- Enemies ----------------
        # pass the full enemy list so each enemy can separate & climb over others
        for e in self.enemies:
            e.update(dt, self.player.rect, solids, self.enemies)

        # cleanup
        self.bullets = [b for b in self.bullets if b.alive]
        self.enemies = [e for e in self.enemies if not e.dead]

        # death -> respawn
        if self.player.health <= 0:
            self._respawn(full_heal=True)

        # fall -> respawn (no heal)
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

        for b in self.bullets:
            b.draw(surf, camera)

        for e in self.enemies:
            e.draw(surf, camera)

        self.player.draw(surf, camera)