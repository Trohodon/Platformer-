# entities/player.py
import pygame

from core.settings import (
    GRAVITY, MAX_FALL_SPEED, MOVE_SPEED, JUMP_SPEED, PLAYER_COLOR,
    DASH_SPEED, DASH_TIME, DASH_COOLDOWN, AIR_DASHES,
    WALL_SLIDE_SPEED, WALL_JUMP_X, WALL_JUMP_Y, WALL_STICK_TIME
)
from core.utils import clamp


class Player:
    def __init__(self, x: float, y: float):
        self.rect = pygame.Rect(int(x), int(y), 32, 44)
        self.vel = pygame.Vector2(0, 0)
        self.on_ground = False

        # ---- Health ----
        self.max_health = 100
        self.health = 100
        self.hurt_iframes = 0.40   # seconds of invulnerability after damage
        self.hurt_timer = 0.0

        # --- Jumping ---
        self.max_jumps = 2
        self.jumps_left = self.max_jumps

        self.coyote_time = 0.10
        self.coyote_timer = 0.0

        self.jump_buffer_time = 0.12
        self.jump_buffer_timer = 0.0

        self.jump_cut_multiplier = 0.45
        self.was_on_ground = False

        # --- Wall state ---
        self.on_wall_left = False
        self.on_wall_right = False
        self.wall_stick_timer = 0.0

        # --- Dash state ---
        self.dashing = False
        self.dash_timer = 0.0
        self.dash_cooldown = 0.0
        self.air_dashes_left = AIR_DASHES
        self._dash_dir = 1

    def take_damage(self, amount: int) -> bool:
        """Returns True if damage was applied."""
        if self.hurt_timer > 0.0:
            return False
        self.health = max(0, self.health - int(amount))
        self.hurt_timer = self.hurt_iframes
        return True

    def update(self, dt: float, input_state,
               jump_pressed: bool, jump_released: bool, jump_held: bool,
               dash_pressed: bool, solids):

        # timers
        self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)
        self.coyote_timer = max(0.0, self.coyote_timer - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.wall_stick_timer = max(0.0, self.wall_stick_timer - dt)
        self.hurt_timer = max(0.0, self.hurt_timer - dt)

        # horizontal intent
        move = 0.0
        if input_state.left():
            move -= 1.0
        if input_state.right():
            move += 1.0

        if move != 0:
            self._dash_dir = 1 if move > 0 else -1

        # jump buffer
        if jump_pressed:
            self.jump_buffer_timer = self.jump_buffer_time

        # dash trigger
        if dash_pressed and (not self.dashing) and self.dash_cooldown <= 0.0:
            can_dash = self.on_ground or (self.air_dashes_left > 0)
            if can_dash:
                self.dashing = True
                self.dash_timer = DASH_TIME
                self.dash_cooldown = DASH_COOLDOWN
                if not self.on_ground:
                    self.air_dashes_left -= 1
                self.vel.x = self._dash_dir * DASH_SPEED
                self.vel.y = 0

        # dash physics
        if self.dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0:
                self.dashing = False
            self._move_x(dt, solids)
            self._move_y(dt, solids)
        else:
            self.vel.x = move * MOVE_SPEED
            self.vel.y += GRAVITY * dt
            self.vel.y = clamp(self.vel.y, -99999.0, MAX_FALL_SPEED)
            self._move_x(dt, solids)
            self._move_y(dt, solids)

        # update wall flags
        self._update_wall_flags(solids)

        # coyote time
        if self.on_ground:
            self.coyote_timer = self.coyote_time

        # landing resets
        if self.on_ground and not self.was_on_ground:
            self.jumps_left = self.max_jumps
            self.air_dashes_left = AIR_DASHES

        # wall stick when contacting wall in air while falling
        if (self.on_wall_left or self.on_wall_right) and (not self.on_ground) and self.vel.y > 0:
            self.wall_stick_timer = WALL_STICK_TIME

        # wall slide
        sliding = False
        if not self.on_ground and self.vel.y > 0:
            if self.on_wall_left and input_state.left():
                sliding = True
            if self.on_wall_right and input_state.right():
                sliding = True
        if sliding:
            self.vel.y = min(self.vel.y, WALL_SLIDE_SPEED)

        # consume buffered jump
        if self.jump_buffer_timer > 0.0:
            if not self.on_ground and (self.on_wall_left or self.on_wall_right) and self.wall_stick_timer > 0.0:
                self._do_wall_jump()
                self.jump_buffer_timer = 0.0
                self.coyote_timer = 0.0
            else:
                if (self.on_ground or self.coyote_timer > 0.0) and self.jumps_left > 0:
                    self._do_jump()
                    self.jump_buffer_timer = 0.0
                    self.coyote_timer = 0.0
                elif (not self.on_ground) and self.jumps_left > 0:
                    self._do_jump()
                    self.jump_buffer_timer = 0.0

        # variable jump height
        if jump_released and self.vel.y < 0:
            self.vel.y *= self.jump_cut_multiplier

        self.was_on_ground = self.on_ground

    def _move_x(self, dt: float, solids):
        self.rect.x += int(self.vel.x * dt)
        for s in solids:
            if self.rect.colliderect(s):
                if self.vel.x > 0:
                    self.rect.right = s.left
                elif self.vel.x < 0:
                    self.rect.left = s.right
                self.vel.x = 0

    def _move_y(self, dt: float, solids):
        self.rect.y += int(self.vel.y * dt)
        self.on_ground = False
        for s in solids:
            if self.rect.colliderect(s):
                if self.vel.y > 0:
                    self.rect.bottom = s.top
                    self.vel.y = 0
                    self.on_ground = True
                elif self.vel.y < 0:
                    self.rect.top = s.bottom
                    self.vel.y = 0

    def _update_wall_flags(self, solids):
        self.on_wall_left = False
        self.on_wall_right = False
        if self.on_ground:
            return
        left_probe = self.rect.move(-1, 0)
        right_probe = self.rect.move(1, 0)
        for s in solids:
            if left_probe.colliderect(s):
                self.on_wall_left = True
            if right_probe.colliderect(s):
                self.on_wall_right = True
            if self.on_wall_left and self.on_wall_right:
                break

    def _do_jump(self):
        self.vel.y = -JUMP_SPEED
        self.on_ground = False
        self.jumps_left -= 1

    def _do_wall_jump(self):
        if self.on_wall_left:
            self.vel.x = WALL_JUMP_X
        elif self.on_wall_right:
            self.vel.x = -WALL_JUMP_X
        self.vel.y = -WALL_JUMP_Y
        self.wall_stick_timer = 0.0
        if self.jumps_left == self.max_jumps:
            self.jumps_left -= 1

    def draw(self, surf: pygame.Surface, camera):
        pygame.draw.rect(surf, PLAYER_COLOR, camera.apply(self.rect))