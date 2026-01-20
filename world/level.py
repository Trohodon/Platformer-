# world/level.py
import pygame
import random

from core.settings import TILE_SIZE
from world.loader import load_demo_level
from world.tilemap import Tilemap
from entities.player import Player
from entities.enemy import Enemy
from entities.powerup import PowerUp
from world.wave_powerups import WAVE_POWERUPS


def clamp_int(v: int, lo: int, hi: int) -> int:
    return lo if v < lo else hi if v > hi else v


class WaveSystem:
    """
    Dedicated wave config:
    - Define each wave as list of spawns: (enemy_kind, count)
    - Easy to add future enemy kinds without rewriting Level
    """
    def __init__(self):
        self.wave_number = 0

        # EDIT THESE:
        self.waves = {
            1: [("grunt", 6)],
            2: [("grunt", 9)],
            3: [("grunt", 12)],
            4: [("grunt", 14)],
            5: [("grunt", 18)],
            6: [("grunt", 22)],
            7: [("grunt", 26)],
            8: [("grunt", 30)],
            9: [("grunt", 32)],
            10: [("grunt", 34)],
        }

        self.wave_cooldown = 1.2
        self.timer = 0.6
        self.active = False

    def next_wave_spawns(self):
        self.wave_number += 1
        return self.waves.get(self.wave_number, [("grunt", 10 + self.wave_number * 2)])


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
        self.powerups = []

        self.spawn_y = -TILE_SIZE * 6
        self.drop_points = self._build_drop_points()

        self.waves = WaveSystem()
        self._spawn_rng = random.Random(1337)

    def _compute_world_rect(self) -> pygame.Rect:
        rows = len(self.grid)
        cols = max((len(r) for r in self.grid), default=0)
        return pygame.Rect(0, 0, cols * TILE_SIZE, rows * TILE_SIZE)

    def _find_player_spawn(self) -> pygame.Vector2:
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch == "P":
                    return pygame.Vector2(x * TILE_SIZE + 8, y * TILE_SIZE + 2)
        return pygame.Vector2(TILE_SIZE * 2, TILE_SIZE * 2)

    def _build_drop_points(self):
        rows = len(self.grid)
        cols = max((len(r) for r in self.grid), default=0)
        if rows == 0 or cols == 0:
            return []

        solids = {"#", "C", "M"}
        open_cols = []
        check_depth = min(12, rows)

        for x in range(cols):
            blocked = False
            for y in range(check_depth):
                if x < len(self.grid[y]) and self.grid[y][x] in solids:
                    blocked = True
                    break
            if not blocked:
                open_cols.append(x)

        points = [x * TILE_SIZE + TILE_SIZE // 2 for x in open_cols]

        px = self.player.rect.centerx
        min_dx = TILE_SIZE * 6
        filtered = [wx for wx in points if abs(wx - px) > min_dx]
        return filtered if len(filtered) >= 6 else points

    def _make_enemy(self, kind: str, x: float, y: float):
        # Future-proof: if Enemy supports kind param, use it; otherwise ignore.
        try:
            return Enemy(x, y, radius=16, kind=kind)
        except TypeError:
            return Enemy(x, y, radius=16)

    def _spawn_powerups_for_wave(self, wave_num: int):
        ids = WAVE_POWERUPS.get(wave_num, [])
        if not ids:
            return
        if not self.drop_points:
            return

        rng = self._spawn_rng
        for pid in ids:
            x = self.drop_points[rng.randrange(len(self.drop_points))] + rng.randint(-10, 10)
            y = TILE_SIZE * 2
            self.powerups.append(PowerUp(pid, x, y))

    def _start_next_wave(self):
        spawns = self.waves.next_wave_spawns()
        self.waves.active = True

        self.enemies.clear()

        if not self.drop_points:
            return

        rng = random.Random(self.waves.wave_number * 99173)

        hubs = [self.drop_points[rng.randrange(len(self.drop_points))] for _ in range(rng.randint(2, 3))]

        def pick_drop_x():
            hx = hubs[rng.randrange(len(hubs))]
            idx = min(range(len(self.drop_points)), key=lambda i: abs(self.drop_points[i] - hx))
            spread = rng.randint(2, 6)
            j = clamp_int(idx + rng.randint(-spread, spread), 0, len(self.drop_points) - 1)
            return self.drop_points[j]

        total = 0
        for _, c in spawns:
            total += int(c)

        i = 0
        for kind, count in spawns:
            for _ in range(int(count)):
                ex = pick_drop_x() + rng.randint(-10, 10)
                ey = self.spawn_y - i * 10
                self.enemies.append(self._make_enemy(kind, ex, ey))
                i += 1

        self._spawn_powerups_for_wave(self.waves.wave_number)

    def update(self, dt, input_state, jump_pressed, jump_released, jump_held, dash_pressed, shoot_pressed):
        solids = self.tilemap.get_solid_rects_near(self.player.rect)

        # Player
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

        # Player spikes
        for spike in self.tilemap.spikes:
            if self.player.rect.colliderect(spike):
                self.player.take_damage(self.player.abilities.spike_damage)
                break

        # Waves
        if not self.waves.active:
            self.waves.timer -= dt
            if self.waves.timer <= 0.0:
                self._start_next_wave()
        else:
            if len([e for e in self.enemies if not getattr(e, "dead", False)]) == 0:
                self.waves.active = False
                self.waves.timer = self.waves.wave_cooldown
                self.enemies.clear()

        # Powerups
        for p in self.powerups:
            p.update(dt)

        for p in self.powerups:
            if not p.alive:
                continue
            if self.player.rect.colliderect(p.rect):
                self.player.abilities.add_stack(p.power_id, 1)
                # refresh max health immediately
                self.player.max_health = self.player.abilities.max_health
                self.player.health = min(self.player.health, self.player.max_health)
                p.alive = False

        self.powerups = [p for p in self.powerups if p.alive]

        # Bullets
        for b in self.bullets:
            b.update(dt, solids)

        # Bullet -> enemy hits
        for b in self.bullets:
            if not b.alive:
                continue
            br = b.rect
            for e in self.enemies:
                if getattr(e, "dead", False):
                    continue
                if br.colliderect(e.rect):
                    e.take_damage(b.damage)
                    b.alive = False
                    break

        # Enemies
        for e in self.enemies:
            e.update(dt, self.player.rect, solids, self.grid, self.enemies)

            # Enemy spikes (same as player)
            for spike in self.tilemap.spikes:
                if e.rect.colliderect(spike):
                    # if Enemy has take_damage
                    try:
                        e.take_damage(self.player.abilities.spike_damage)
                    except Exception:
                        pass
                    break

            # clamp X to world so dashes don't escape map
            if e.pos.x < self.world_rect.left + e.radius:
                e.pos.x = self.world_rect.left + e.radius
                e.vel.x = 0.0
                if hasattr(e, "dashing"):
                    e.dashing = False
                if hasattr(e, "dash_timer"):
                    e.dash_timer = 0.0

            if e.pos.x > self.world_rect.right - e.radius:
                e.pos.x = self.world_rect.right - e.radius
                e.vel.x = 0.0
                if hasattr(e, "dashing"):
                    e.dashing = False
                if hasattr(e, "dash_timer"):
                    e.dash_timer = 0.0

        # solid enemy-vs-enemy
        self._resolve_enemy_collisions()

        # respawn enemies that fall out
        self._respawn_fallen_enemies()

        # cleanup
        self.bullets = [b for b in self.bullets if b.alive]
        self.enemies = [e for e in self.enemies if not getattr(e, "dead", False)]

        # player respawn logic
        if self.player.health <= 0:
            self._respawn_player(full_heal=True)
        if self.player.rect.top > self.fall_y:
            self._respawn_player(full_heal=False)

    def _resolve_enemy_collisions(self):
        n = len(self.enemies)
        for i in range(n):
            a = self.enemies[i]
            if getattr(a, "dead", False):
                continue
            for j in range(i + 1, n):
                b = self.enemies[j]
                if getattr(b, "dead", False):
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

        rng = random.Random(self.waves.wave_number * 2467 + 1337)

        for e in self.enemies:
            if getattr(e, "dead", False):
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

    def _respawn_player(self, full_heal: bool):
        self.player.rect.topleft = self.respawn_point
        self.player.pos.update(self.player.rect.topleft)
        self.player.vel.xy = (0, 0)
        if full_heal:
            self.player.health = self.player.max_health
            self.player.hurt_timer = 0.0

    def draw(self, surf, camera):
        self.tilemap.draw(surf, camera)

        for p in self.powerups:
            p.draw(surf, camera)

        for b in self.bullets:
            b.draw(surf, camera)

        for e in self.enemies:
            e.draw(surf, camera)

        self.player.draw(surf, camera)