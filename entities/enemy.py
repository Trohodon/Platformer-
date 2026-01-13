# entities/enemy.py
import pygame

from core.settings import GRAVITY, MAX_FALL_SPEED, TILE_SIZE
from core.utils import clamp


class Enemy:
    """
    Circle enemy with simple "separation" + climbing behavior:
    - Chases player
    - Jumps if blocked OR if another enemy is blocking (to climb over)
    - Applies a small separation force so they don't blob into one stack
    """

    def __init__(self, x: float, y: float, radius: int = 16):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 0)
        self.radius = radius

        self.max_health = 60
        self.health = 60
        self.dead = False

        self.speed = 230.0
        self.jump_speed = 780.0

        self.on_ground = False
        self.jump_cd = 0.0

        # spacing behavior
        self.sep_strength = 420.0   # how hard they push away from neighbors
        self.sep_range = radius * 3 # how far they "feel" other enemies

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.pos.x - self.radius),
            int(self.pos.y - self.radius),
            self.radius * 2,
            self.radius * 2
        )

    def take_damage(self, dmg: int):
        if self.dead:
            return
        self.health -= int(dmg)
        if self.health <= 0:
            self.dead = True

    def update(self, dt: float, player_rect: pygame.Rect, solids, neighbors):
        if self.dead:
            return

        self.jump_cd = max(0.0, self.jump_cd - dt)

        # ------------------------------------------------------
        # 1) Base chase (toward player)
        # ------------------------------------------------------
        dx = player_rect.centerx - self.pos.x
        move_dir = 0.0
        if abs(dx) > 6:
            move_dir = 1.0 if dx > 0 else -1.0

        desired_vx = move_dir * self.speed

        # ------------------------------------------------------
        # 2) Separation force (prevents blob behavior)
        #    Push away from nearby enemies so they spread out
        # ------------------------------------------------------
        sep = pygame.Vector2(0, 0)
        for other in neighbors:
            if other is self or other.dead:
                continue
            d = self.pos - other.pos
            dist = d.length()
            if dist <= 0.001:
                continue
            if dist < self.sep_range:
                # normalized push scaled by closeness
                strength = (1.0 - (dist / self.sep_range))
                sep += (d / dist) * strength

        # apply separation mostly to X, lightly to Y
        desired_vx += sep.x * self.sep_strength * dt

        # clamp final vx
        self.vel.x = clamp(desired_vx, -self.speed * 1.35, self.speed * 1.35)

        # ------------------------------------------------------
        # 3) Gravity
        # ------------------------------------------------------
        self.vel.y += GRAVITY * dt
        self.vel.y = clamp(self.vel.y, -99999.0, MAX_FALL_SPEED)

        # ------------------------------------------------------
        # 4) Move/collide with world
        # ------------------------------------------------------
        pre_vx = self.vel.x
        self._move_x(dt, solids)
        self._move_y(dt, solids)

        # ------------------------------------------------------
        # 5) Climb logic (jump to get over obstacles / enemies)
        # ------------------------------------------------------
        player_above = player_rect.centery < (self.pos.y - self.radius - TILE_SIZE // 2)
        close_x = abs(player_rect.centerx - self.pos.x) < (TILE_SIZE * 4)

        # "blocked by wall" if we had velocity intent but got zeroed by collision
        blocked_by_wall = (abs(pre_vx) > 1.0 and abs(self.vel.x) < 1e-3)

        # "blocked by enemy" if there's an enemy immediately in front of us
        blocked_by_enemy = self._blocked_by_enemy(move_dir, neighbors)

        if self.on_ground and self.jump_cd <= 0.0:
            if blocked_by_wall or blocked_by_enemy or (player_above and close_x):
                self.vel.y = -self.jump_speed
                self.on_ground = False
                self.jump_cd = 0.22

    def _blocked_by_enemy(self, move_dir: float, neighbors) -> bool:
        if move_dir == 0.0:
            return False

        my_r = self.rect
        # probe a little ahead at foot/chest height
        probe = my_r.copy()
        probe.x += int(move_dir * (self.radius + 6))
        probe.y += int(self.radius * 0.35)
        probe.height = int(self.radius * 0.9)

        for other in neighbors:
            if other is self or other.dead:
                continue
            if probe.colliderect(other.rect):
                return True
        return False

    def _move_x(self, dt: float, solids):
        self.pos.x += self.vel.x * dt
        r = self.rect
        for s in solids:
            if r.colliderect(s):
                if self.vel.x > 0:
                    self.pos.x = s.left - self.radius
                elif self.vel.x < 0:
                    self.pos.x = s.right + self.radius
                self.vel.x = 0.0
                r = self.rect

    def _move_y(self, dt: float, solids):
        self.pos.y += self.vel.y * dt
        self.on_ground = False
        r = self.rect
        for s in solids:
            if r.colliderect(s):
                if self.vel.y > 0:
                    self.pos.y = s.top - self.radius
                    self.vel.y = 0.0
                    self.on_ground = True
                elif self.vel.y < 0:
                    self.pos.y = s.bottom + self.radius
                    self.vel.y = 0.0
                r = self.rect

    def draw(self, surf: pygame.Surface, camera):
        if self.dead:
            return

        rr = self.rect
        rr_screen = camera.apply(rr)
        cx, cy = rr_screen.center

        pygame.draw.circle(surf, (240, 120, 120), (cx, cy), self.radius)

        # health bar
        bar_w = 40
        bar_h = 6
        pct = max(0.0, min(1.0, self.health / self.max_health))
        fill_w = int(bar_w * pct)

        bx = cx - bar_w // 2
        by = cy - self.radius - 14

        pygame.draw.rect(surf, (40, 40, 55), (bx, by, bar_w, bar_h))
        pygame.draw.rect(surf, (220, 80, 80), (bx, by, fill_w, bar_h))
        pygame.draw.rect(surf, (230, 230, 240), (bx, by, bar_w, bar_h), 1)