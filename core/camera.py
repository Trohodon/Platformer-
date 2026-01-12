# core/camera.py
import pygame
from core.settings import WIDTH, HEIGHT, CAMERA_LERP

class Camera:
    def __init__(self):
        self.pos = pygame.Vector2(0, 0)

    def update(self, target_rect: pygame.Rect):
        # Center camera on target
        desired = pygame.Vector2(
            target_rect.centerx - WIDTH * 0.5,
            target_rect.centery - HEIGHT * 0.5
        )
        self.pos += (desired - self.pos) * CAMERA_LERP

    def apply(self, rect: pygame.Rect) -> pygame.Rect:
        return rect.move(-int(self.pos.x), -int(self.pos.y))