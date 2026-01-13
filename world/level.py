# world/level.py  (FULL FILE update using WaveManager + wave definitions)
import pygame
import random

from core.settings import TILE_SIZE
from world.loader import load_demo_level
from world.tilemap import Tilemap
from entities.player import Player
from entities.enemy import Enemy

from world.waves import WaveManager
from world.wave_defs import WAVES


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

        # drop-in spawning
        self.spawn_y = -TILE_SIZE * 6
        self.drop_points = self._build_drop_points()

        # dedicated wave system
        self.waves = WaveManager(WAVES, cooldown=1.2)

        # deterministic per-run RNG for spawn picking
        self._spawn_rng = random.Random(12345)

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

    # ------------------------------------------------------------
    # Wave Spawning
    # ------------------------------------------------------------
    def _spawn_wave(self):
        wave_def = self.waves.current_wave_def()
        if wave_def is None:
            return

        # seed RNG from wave number so wave spawns feel stable
        self._spawn_rng = random.Random(self.waves.wave_number * 99991 + 1337)

        # choose 2-3 hubs so enemies pour in from "areas"
        if not self.drop_points:
            return
        hubs = [self.drop_points[self._spawn_rng.randrange(len(self.drop_points))] for _ in range(self._spawn_rng.randint(2, 3))]

        def pick_drop_x():
            hx = hubs[self._spawn_rng.randrange(len(hubs))]
            idx = min(range(len(self.drop_points)), key=lambda i: abs(self.drop_points[i] - hx))
            spread = self._spawn_rng.randint(2, 6)
            j = clamp_int(idx + self._spawn_rng.randint(-spread, spread), 0, len(self.drop_points) - 1)
            return self.drop_points[j]

        # spawn entries
        spawn_list = []
        for entry in wave_def.get("entries", []):
            etype = entry.get("type", "basic")
            count = int(entry.get("count", 0))
            for _ in range(count):
                spawn_list.append(etype)

        # stagger y so they don't overlap instantly
        for i, etype in enumerate(spawn_list):
            ex = pick_drop_x() + self._spawn_rng.randint(-10, 10)
            ey = self.spawn_y - i * 10

            enemy = self._create_enemy(etype, ex, ey)
            self.enemies.append(enemy)

        self.waves.mark_wave_started()

    def _create_enemy(self, etype: str, x: float, y: float):
        # Future-proof: add new enemy classes here later.
        # For now, everything maps to Enemy (basic).
        if etype == "basic":
            return Enemy(x, y, radius=16)

        # fallback
        return Enemy(x, y, radius=16)

    # ------------------------------------------------------------
    # Update
    # ------------------------------------------------------------
    def update(self, dt, input_state, jump_pressed, jump_released, jump_held, dash_pressed, shoot_pressed):
        solids = self.tilemap.get_solid_rects_near(self.player.rect)

        # player
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

        # clamp player
        self.player.rect.left = max(self.world_rect.left, self.player.rect.left)
        self.player.rect.right = min(self.world_rect.right, self.player.rect.right)

        if self.player.on_ground:
            self.respawn_point.update(self.player.rect.topleft)

        # spikes damage
        for spike in self.tilemap.spikes:
            if self.player.rect.colliderect(spike):
                self.player.take_damage(30)
                break

        # ---- wave manager ----
        alive_enemies = len([e for e in self.enemies if not e.dead])
        start_new = self.waves.update(dt, alive_enemies)
        if start_new:
            self.enemies.clear()
            self._spawn_wave()

        # bullets
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

        # enemies
        for e in self.enemies:
            e.update(dt, self.player.rect, solids, self.grid, self.enemies)

            # clamp x so dash can't push them out
            if e.pos.x < self.world_rect.left + e.radius:
                e.pos.x = self.world_rect.left + e.radius
                e.vel.x = 0.0
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

        # respawn fallen enemies (keep wave intact)
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

        rng = self._spawn_rng

        for e in self.enemies:
            if e.dead:
                continue
            if e.rect.top > self.fall_y:
                ex = self.drop_points[rng.randrange(len(self.drop_points))] + rng.randint(-10, 10)
                e.pos.update(ex, self.spawn_y)
                e.vel.update(0, 0)

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