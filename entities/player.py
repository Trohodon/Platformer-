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

    def update(self, dt: float, input_state, jump_requested: bool, solids):
        # Horizontal input
        move = 0.0
        if input_state.left():
            move -= 1.0
        if input_state.right():
            move += 1.0

        self.vel.x = move * MOVE_SPEED

        # Jump (only if grounded)
        if jump_requested and self.on_ground:
            self.vel.y = -JUMP_SPEED
            self.on_ground = False

        # Gravity
        self.vel.y += GRAVITY * dt
        self.vel.y = clamp(self.vel.y, -99999.0, MAX_FALL_SPEED)

        # Move & collide (separate axis resolution)
        self._move_x(dt, solids)
        self._move_y(dt, solids)

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