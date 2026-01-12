# core/input.py
import pygame

class Input:
    def __init__(self):
        self._keys = None

    def update(self):
        self._keys = pygame.key.get_pressed()

    def left(self) -> bool:
        k = self._keys
        return bool(k[pygame.K_a] or k[pygame.K_LEFT])

    def right(self) -> bool:
        k = self._keys
        return bool(k[pygame.K_d] or k[pygame.K_RIGHT])

    def jump_pressed(self) -> bool:
        # "pressed this frame" will be handled via KEYDOWN events
        return False