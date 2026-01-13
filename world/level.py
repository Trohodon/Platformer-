# world/level.py  (FULL FILE update: clamp + respawn enemies that leave the world)
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

        self.enemies = []
        self.bullets = []

        # waves
        self.wave_index = 0
        self.wave_active = False
        self.wave_cooldown = 1.2
        self.wave_timer = 0.6

        # drop-in spawning
        self.spawn_y = -TILE_SIZE * 6
        self.drop_points = self._build_drop_points()

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

    def _build_drop_points(self):
        rows = len(self.grid)
        cols = len(self.grid[0]) if rows else 0
        if rows == 0 or cols == 0:
            return []

        solids = {"#", "C", "M"}
        open_cols = []
        check_depth = min(12, rows)

        for x in range(cols):
            blocked = False
            for y in range(check_depth):
                if self.grid[y][x] in solids:
                    blocked = True
                    break
            if not blocked:
                open_cols.append(x)

        points = [x * TILE_SIZE + TILE_SIZE // 2 for x in open_cols]

        px = self.player.rect.centerx
        min_dx = TILE_SIZE * 6
        filtered = [wx for wx in points if abs(wx - px) > min_dx]
        return filtered if len(filtered) >= 6 else points

    def _start_next_wave(self):
        self.wave_index += 1
        self.wave_active = True

        base = 6
        add = min(22, self.wave_index * 2)
        count = min(34, base + add)

        rng = random.Random(self.wave_index * 99173)
        if not self.drop_points:
            return

        hubs = [self.drop_points[rng.randrange(len(self.drop_points))] for _ in range(rng.randint(2, 3))]

        def pick_drop_x():
            hx = hubs[rng.randrange(len(hubs))]
            idx = min(range(len(self.drop_points)), key=lambda i: abs(self.drop_points[i] - hx))
            spread = rng.randint(2, 6)
            j = clamp_int(idx + rng.randint(-spread, spread), 0, len(self.drop_points) - 1)
            return self.drop_points[j]

        self.enemies.clear()

        for i in range(count):
            ex = pick_drop_x() + rng.randint(-10, 10)
            ey = self.spawn_y - i * 10
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

        if shoot_pressed:
            b = self.player.try_shoot()
            if b is not None:
                self.bullets.append(b)

        # clamp player to world
        self.player.rect.left = max(self.world_rect.left, self.player.rect.left)
        self.player.rect.right = min(self.world_rect.right, self.player.rect.right)

        if self.player.on_ground:
            self.respawn_point.update(self.player.rect.topleft)

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
            if len([e for e in self.enemies if not e.dead]) == 0:
                self.wave_active = False
                self.wave_timer = self.wave_cooldown
                self.enemies.clear()

        # ---------------- Bullets ----------------
        for b in self.bullets:
            b.update(dt, solids)

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
        for e in self.enemies:
            e.update(dt, self.player.rect, solids, self.grid, self.enemies)

            # HARD CLAMP X so dashes cannot push them outside the world
            if e.pos.x < self.world_rect.left + e.radius:
                e.pos.x = self.world_rect.left + e.radius
                e.vel.x = 0.0
                # cancel dash if it was driving them out
                if getattr(e, "dashing", False):
                    e.dashing = False
                    e.dash_timer = 0.0

            if e.pos.x > self.world_rect.right - e.radius:
                e.pos.x = self.world_rect.right - e.radius
                e.vel.x = 0.0
                if getattr(e, "dashing", False):
                    e.dashing = False
                    e.dash_timer = 0.0

        # solid enemy-vs-enemy
        self._resolve_enemy_collisions()

        # respawn enemies that fall out of the arena
        self._respawn_fallen_enemies()

        # cleanup
        self.bullets = [b for b in self.bullets if b.alive]
        self.enemies = [e for e in self.enemies if not e.dead]

        # player respawns
        if self.player.health <= 0:
            self._respawn_player(full_heal=True)

        if self.player.rect.top > self.fall_y:
            self._respawn_player(full_heal=False)

    def _resolve_enemy_collisions(self):
        n = len(self.enemies)
        for i in range(n):
            a = self.enemies[i]
            if a.dead:
                continue
            for j in range(i + 1, n):
                b = self.enemies[j]
                if b.dead:
                    continue

                d = b.pos - a.pos
                dist = d.length()
                min_dist = a.radius + b.radius

                if dist <= 0.001:
                    d = pygame.Vector2(1, 0)
                    dist = 1.0

                if dist < min_dist:
                    overlap = (min_dist - dist)
                    nrm = d / dist
                    push = nrm * (overlap * 0.5)
                    a.pos -= push
                    b.pos += push
                    a.vel.x *= 0.95
                    b.vel.x *= 0.95

    def _respawn_fallen_enemies(self):
        if not self.drop_points:
            return

        rng = random.Random(self.wave_index * 2467 + 1337)

        for e in self.enemies:
            if e.dead:
                continue

            # if they fell below the world, respawn above
            if e.rect.top > self.fall_y:
                ex = self.drop_points[rng.randrange(len(self.drop_points))] + rng.randint(-10, 10)
                e.pos.update(ex, self.spawn_y)
                e.vel.update(0, 0)

                # reset enemy "player-like" movement states if present
                if hasattr(e, "dashing"):
                    e.dashing = False
                if hasattr(e, "dash_timer"):
                    e.dash_timer = 0.0
                if hasattr(e, "dash_cd"):
                    e.dash_cd = 0.15
                if hasattr(e, "air_dashes_left") and hasattr(e, "air_dashes_max"):
                    e.air_dashes_left = e.air_dashes_max
                if hasattr(e, "jumps_left") and hasattr(e, "max_jumps"):
                    e.jumps_left = e.max_jumps
                if hasattr(e, "path"):
                    e.path = []
                    e.path_index = 0
                    e.repath_timer = 0.0

    def _respawn_player(self, full_heal: bool):
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


def clamp_int(v: int, lo: int, hi: int) -> int:
    return lo if v < lo else hi if v > hi else v