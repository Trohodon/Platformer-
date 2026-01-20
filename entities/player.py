# entities/player.py
import pygame
from typing import Optional

from core.abilities import Abilities
from entities.bullet import Bullet


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


class Player:
    """
    Movement uses pygame.key.get_pressed() (hard-fixed input).
    Adds wall slide + wall jump:
      - If you're in the air and touching a wall, you can jump off it.
      - Wall jump pushes away from the wall and gives an upward boost.
      - Includes a short "wall lock" so you don't instantly re-stick.
    """

    def __init__(self, x: float, y: float):
        self.rect = pygame.Rect(int(x), int(y), 22, 34)
        self.pos = pygame.Vector2(self.rect.x, self.rect.y)
        self.vel = pygame.Vector2(0, 0)

        self.on_ground = False
        self.facing = 1

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

        # wall mechanics
        self.wall_dir = 0            # -1 touching wall on left, +1 on right, 0 none
        self.wall_slide_speed = 320  # clamp fall speed while sliding
        self.wall_jump_x = 520       # horizontal push
        self.wall_jump_y_mult = 1.00 # multiplier on normal jump strength
        self.wall_lock = 0.0         # prevents immediate re-stick after wall jump

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
        return Bullet(bx, by, vx, 0.0, damage=self.abilities.bullet_damage)

    def update(
        self,
        dt: float,
        input_state,  # kept for compatibility; movement reads keyboard directly
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
        if self.wall_lock > 0.0:
            self.wall_lock = max(0.0, self.wall_lock - dt)

        # regen
        if self.abilities.regen_per_sec > 0.0 and self.health > 0:
            self.health = min(self.max_health, int(self.health + self.abilities.regen_per_sec * dt))

        # movement input
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

        # jump buffer + coyote
        if jump_pressed:
            self.jump_buffer = 0.12
        else:
            self.jump_buffer = max(0.0, self.jump_buffer - dt)

        if self.on_ground:
            self.coyote = 0.10
        else:
            self.coyote = max(0.0, self.coyote - dt)

        # dash
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

        # wall detection (requires current rect + solids)
        if self.wall_lock <= 0.0 and (not self.on_ground):
            self.wall_dir = self._detect_wall(solids)
        else:
            self.wall_dir = 0

        # wall slide clamp (only if moving downward)
        if self.wall_dir != 0 and self.vel.y > self.wall_slide_speed:
            self.vel.y = self.wall_slide_speed

        # perform wall jump if buffered and on wall
        # priority: wall jump -> normal jump
        if self.jump_buffer > 0.0 and self.wall_dir != 0 and not self.on_ground:
            # push away from wall
            away = -self.wall_dir
            self.vel.x = away * self.wall_jump_x
            self.vel.y = -self.abilities.jump_speed * self.wall_jump_y_mult

            # give a brief lock so you don't re-stick instantly
            self.wall_lock = 0.16
            self.wall_dir = 0

            # reset buffer and allow extra jumps after wall jump
            self.jump_buffer = 0.0
            self.jumps_left = max(0, self.abilities.max_jumps - 1)

        # dash update / normal movement
        if self.dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0.0:
                self.dashing = False
                self.dash_cd = self.abilities.dash_cooldown
        else:
            # horizontal accel
            target = move_x * self.abilities.run_speed
            accel = 3600.0 if self.on_ground else (2400.0 * self.abilities.air_control)

            # while on wall, slightly reduce "stickiness" if pushing into wall
            if self.wall_dir != 0 and ((move_x < 0 and self.wall_dir < 0) or (move_x > 0 and self.wall_dir > 0)):
                accel *= 0.45

            diff = target - self.vel.x
            step = accel * dt
            if diff > step:
                diff = step
            elif diff < -step:
                diff = -step
            self.vel.x += diff

            # gravity
            self.vel.y = min(self.max_fall, self.vel.y + self.gravity * dt)

            # normal buffered jump
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

    def _detect_wall(self, solids) -> int:
        """
        Returns:
          -1 if touching wall on left
          +1 if touching wall on right
           0 otherwise
        Uses a 1px probe on each side.
        """
        # probe rectangles
        left_probe = pygame.Rect(self.rect.left - 1, self.rect.top + 2, 1, self.rect.height - 4)
        right_probe = pygame.Rect(self.rect.right, self.rect.top + 2, 1, self.rect.height - 4)

        hit_left = False
        hit_right = False

        for s in solids:
            if left_probe.colliderect(s):
                hit_left = True
            if right_probe.colliderect(s):
                hit_right = True
            if hit_left and hit_right:
                break

        if hit_left and not hit_right:
            return -1
        if hit_right and not hit_left:
            return +1
        return 0

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