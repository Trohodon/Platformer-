# entities/player.py
import pygame
from typing import Optional

from core.abilities import Abilities
from entities.bullet import Bullet


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


class Player:
    def __init__(self, x: float, y: float):
        self.rect = pygame.Rect(int(x), int(y), 22, 34)
        self.pos = pygame.Vector2(self.rect.x, self.rect.y)
        self.vel = pygame.Vector2(0, 0)

        self.on_ground = False
        self.facing = 1  # -1 left, +1 right

        self.abilities = Abilities()

        self.max_health = self.abilities.max_health
        self.health = self.max_health

        # timers
        self.hurt_timer = 0.0
        self.shoot_cd = 0.0

        # jumping
        self.jumps_left = max(0, self.abilities.max_jumps - 1)
        self.jump_buffer = 0.0
        self.coyote = 0.0

        # dash
        self.dashing = False
        self.dash_timer = 0.0
        self.dash_cd = 0.0
        self.air_dashes_left = self.abilities.air_dashes_max
        self.dash_dir = 1

        # physics feel
        self.gravity = 2200.0
        self.max_fall = 1200.0

    def take_damage(self, amount: int) -> bool:
        if self.hurt_timer > 0.0:
            return False
        dmg = int(max(1, int(amount) * self.abilities.damage_taken_mult))
        self.health = max(0, self.health - dmg)
        self.hurt_timer = self.abilities.i_frames
        return True

    def try_shoot(self) -> Optional[Bullet]:
        if self.shoot_cd > 0.0:
            return None

        self.shoot_cd = self.abilities.fire_rate

        bx = self.rect.centerx + (self.facing * 10)
        by = self.rect.centery - 6

        vx = self.facing * self.abilities.bullet_speed
        vy = 0.0
        return Bullet(bx, by, vx, vy, damage=self.abilities.bullet_damage)

    def update(
        self,
        dt: float,
        input_state,  # kept for compatibility; movement ignores it
        jump_pressed: bool,
        jump_released: bool,
        jump_held: bool,
        dash_pressed: bool,
        solids,
    ):
        # refresh derived caps (powerups)
        new_max = self.abilities.max_health
        if new_max != self.max_health:
            self.max_health = new_max
            self.health = min(self.health, self.max_health)

        # timers
        if self.hurt_timer > 0.0:
            self.hurt_timer = max(0.0, self.hurt_timer - dt)
        if self.shoot_cd > 0.0:
            self.shoot_cd = max(0.0, self.shoot_cd - dt)
        if self.dash_cd > 0.0:
            self.dash_cd = max(0.0, self.dash_cd - dt)

        # regen
        if self.abilities.regen_per_sec > 0.0 and self.health > 0:
            self.health = min(
                self.max_health,
                int(self.health + self.abilities.regen_per_sec * dt),
            )

        # -------------------------
        # Movement input (HARD FIX)
        # -------------------------
        keys = pygame.key.get_pressed()
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]

        move_x = 0
        if left:
            move_x -= 1
        if right:
            move_x += 1

        if move_x != 0:
            self.facing = 1 if move_x > 0 else -1

        # -------------------------
        # Jump buffer + coyote
        # -------------------------
        if jump_pressed:
            self.jump_buffer = 0.12
        else:
            self.jump_buffer = max(0.0, self.jump_buffer - dt)

        if self.on_ground:
            self.coyote = 0.10
        else:
            self.coyote = max(0.0, self.coyote - dt)

        # -------------------------
        # Dash
        # -------------------------
        if dash_pressed and (not self.dashing) and self.dash_cd <= 0.0:
            can_dash = self.on_ground or (self.air_dashes_left > 0)
            if can_dash:
                self.dashing = True
                self.dash_timer = self.abilities.dash_time
                self.dash_dir = self.facing if move_x == 0 else (1 if move_x > 0 else -1)
                self.vel.y = 0.0
                self.vel.x = self.dash_dir * self.abilities.dash_speed
                if not self.on_ground:
                    self.air_dashes_left -= 1

        if self.dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0.0:
                self.dashing = False
                self.dash_cd = self.abilities.dash_cooldown
        else:
            # horizontal acceleration
            target = move_x * self.abilities.run_speed
            accel = 3600.0 if self.on_ground else (2400.0 * self.abilities.air_control)

            diff = target - self.vel.x
            step = accel * dt
            if diff > step:
                diff = step
            elif diff < -step:
                diff = -step
            self.vel.x += diff

            # gravity
            self.vel.y = min(self.max_fall, self.vel.y + self.gravity * dt)

            # buffered jump
            if self.jump_buffer > 0.0:
                can_jump = self.on_ground or (self.coyote > 0.0) or (self.jumps_left > 0)
                if can_jump:
                    if not (self.on_ground or self.coyote > 0.0):
                        self.jumps_left -= 1
                    self.vel.y = -self.abilities.jump_speed
                    self.on_ground = False
                    self.coyote = 0.0
                    self.jump_buffer = 0.0

        # variable jump height
        if jump_released and self.vel.y < 0:
            self.vel.y *= 0.55

        # move + collide
        self._move_and_collide(dt, solids)

        # reset stocks on ground
        if self.on_ground:
            self.jumps_left = max(0, self.abilities.max_jumps - 1)
            self.air_dashes_left = self.abilities.air_dashes_max

    def _move_and_collide(self, dt: float, solids):
        # X
        self.pos.x += self.vel.x * dt
        self.rect.x = int(self.pos.x)

        for s in solids:
            if self.rect.colliderect(s):
                if self.vel.x > 0:
                    self.rect.right = s.left
                elif self.vel.x < 0:
                    self.rect.left = s.right
                self.pos.x = self.rect.x
                self.vel.x = 0.0

        # Y
        self.pos.y += self.vel.y * dt
        self.rect.y = int(self.pos.y)

        self.on_ground = False
        for s in solids:
            if self.rect.colliderect(s):
                if self.vel.y > 0:
                    self.rect.bottom = s.top
                    self.on_ground = True
                elif self.vel.y < 0:
                    self.rect.top = s.bottom
                self.pos.y = self.rect.y
                self.vel.y = 0.0

    def draw(self, surf: pygame.Surface, camera):
        rr = camera.apply(self.rect)
        col = (230, 230, 240) if self.hurt_timer <= 0.0 else (255, 180, 180)
        pygame.draw.rect(surf, col, rr)
        pygame.draw.rect(surf, (20, 20, 26), rr, 2)