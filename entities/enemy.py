# entities/enemy.py
import pygame
from core.settings import GRAVITY, MAX_FALL_SPEED, TILE_SIZE
from core.utils import clamp


class Enemy:
    """
    Simple circle enemy that can handle basically any random map:
    - Moves toward player
    - If blocked by wall while grounded -> jumps
    - If player is above and close -> jumps
    - Uses tile collision like the player
    """

    def __init__(self, x: float, y: float, radius: int = 16):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 0)
        self.radius = radius

        self.max_health = 60
        self.health = 60

        self.speed = 220.0
        self.jump_speed = 760.0

        self.on_ground = False
        self.dead = False

        # tiny cooldown so it doesn't spam jump every frame
        self.jump_cd = 0.0

    @property
    def rect(self) -> pygame.Rect:
        # bounding box for collisions
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

    def update(self, dt: float, player_rect: pygame.Rect, solids: list[pygame.Rect]):
        if self.dead:
            return

        self.jump_cd = max(0.0, self.jump_cd - dt)

        # --- horizontal chase ---
        target_x = player_rect.centerx
        dx = target_x - self.pos.x
        move_dir = 0.0
        if abs(dx) > 6:
            move_dir = 1.0 if dx > 0 else -1.0
        self.vel.x = move_dir * self.speed

        # --- gravity ---
        self.vel.y += GRAVITY * dt
        self.vel.y = clamp(self.vel.y, -99999.0, MAX_FALL_SPEED)

        # --- move/collide ---
        self._move_x(dt, solids)
        self._move_y(dt, solids)

        # --- "navigate any map" jump heuristics ---
        player_above = player_rect.centery < (self.pos.y - self.radius - TILE_SIZE // 2)
        close_x = abs(player_rect.centerx - self.pos.x) < (TILE_SIZE * 4)

        # If chasing into wall, _move_x will have zeroed vel.x; treat as blocked
        blocked = (move_dir != 0.0 and abs(self.vel.x) < 1e-3)

        if self.on_ground and self.jump_cd <= 0.0:
            if blocked or (player_above and close_x):
                self.vel.y = -self.jump_speed
                self.on_ground = False
                self.jump_cd = 0.25

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

        cx, cy = camera.apply_point((int(self.pos.x), int(self.pos.y)))
        pygame.draw.circle(surf, (240, 120, 120), (cx, cy), self.radius)

        # health bar above head
        bar_w = 40
        bar_h = 6
        pct = max(0.0, min(1.0, self.health / self.max_health))
        fill_w = int(bar_w * pct)

        bx = cx - bar_w // 2
        by = cy - self.radius - 14

        pygame.draw.rect(surf, (40, 40, 55), (bx, by, bar_w, bar_h))
        pygame.draw.rect(surf, (220, 80, 80), (bx, by, fill_w, bar_h))
        pygame.draw.rect(surf, (230, 230, 240), (bx, by, bar_w, bar_h), 1)