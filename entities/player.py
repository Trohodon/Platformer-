# entities/player.py
import pygame

from core.settings import (
    GRAVITY, MAX_FALL_SPEED, MOVE_SPEED, JUMP_SPEED, PLAYER_COLOR
)
from core.utils import clamp


class Player:
    def __init__(self, x: float, y: float):
        self.rect = pygame.Rect(int(x), int(y), 32, 44)
        self.vel = pygame.Vector2(0, 0)
        self.on_ground = False

        # Jump tuning
        self.max_jumps = 2                 # double jump
        self.jumps_left = self.max_jumps

        self.coyote_time = 0.10            # seconds
        self.coyote_timer = 0.0

        self.jump_buffer_time = 0.12       # seconds
        self.jump_buffer_timer = 0.0

        self.jump_cut_multiplier = 0.45    # release early -> reduce upward velocity
        self.was_on_ground = False

    def update(self, dt: float, input_state, jump_pressed: bool, jump_released: bool, jump_held: bool, solids):
        # Horizontal input
        move = 0.0
        if input_state.left():
            move -= 1.0
        if input_state.right():
            move += 1.0
        self.vel.x = move * MOVE_SPEED

        # Track jump buffer (press slightly early)
        if jump_pressed:
            self.jump_buffer_timer = self.jump_buffer_time
        else:
            self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)

        # Gravity
        self.vel.y += GRAVITY * dt
        self.vel.y = clamp(self.vel.y, -99999.0, MAX_FALL_SPEED)

        # Move & collide (separate axis)
        self._move_x(dt, solids)
        self._move_y(dt, solids)

        # Coyote timer (jump slightly after leaving ground)
        if self.on_ground:
            self.coyote_timer = self.coyote_time
        else:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)

        # Reset jumps when landing
        if self.on_ground and not self.was_on_ground:
            self.jumps_left = self.max_jumps

        # Attempt jump if buffered
        if self.jump_buffer_timer > 0.0:
            # Ground/coyote jump
            if (self.on_ground or self.coyote_timer > 0.0) and self.jumps_left > 0:
                self._do_jump()
                self.jump_buffer_timer = 0.0
                self.coyote_timer = 0.0
            # Air jump (double jump)
            elif (not self.on_ground) and self.jumps_left > 0:
                self._do_jump()
                self.jump_buffer_timer = 0.0

        # Variable jump height: if released while rising, cut jump short
        if jump_released and self.vel.y < 0:
            self.vel.y *= self.jump_cut_multiplier

        self.was_on_ground = self.on_ground

    def _do_jump(self):
        self.vel.y = -JUMP_SPEED
        self.on_ground = False
        self.jumps_left -= 1

    def _move_x(self, dt: float, solids):
        self.rect.x += int(self.vel.x * dt)
        for s in solids:
            if self.rect.colliderect(s):
                if self.vel.x > 0:
                    self.rect.right = s.left
                elif self.vel.x < 0:
                    self.rect.left = s.right

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

    def draw(self, surf: pygame.Surface, camera):
        pygame.draw.rect(surf, PLAYER_COLOR, camera.apply(self.rect))