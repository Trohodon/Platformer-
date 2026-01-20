# entities/powerup.py
import pygame
import math
from world.powerup_defs import POWERUPS


class PowerUp:
    def __init__(self, power_id: str, x: float, y: float):
        self.power_id = power_id
        self.pos = pygame.Vector2(x, y)
        self.radius = 12
        self.alive = True
        self.t = 0.0

        p = POWERUPS.get(power_id)
        self.color = p["color"] if p else (200, 200, 200)

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.pos.x - self.radius),
            int(self.pos.y - self.radius),
            self.radius * 2,
            self.radius * 2,
        )

    def update(self, dt: float):
        self.t += dt

    def draw(self, surf: pygame.Surface, camera):
        if not self.alive:
            return

        rr = camera.apply(self.rect)
        cx, cy = rr.center
        cy += int(math.sin(self.t * 3.5) * 4)

        pygame.draw.circle(surf, (*self.color, 60), (cx, cy), self.radius + 8)
        pygame.draw.circle(surf, (*self.color, 120), (cx, cy), self.radius + 4)

        pts = [
            (cx, cy - self.radius),
            (cx + self.radius, cy),
            (cx, cy + self.radius),
            (cx - self.radius, cy),
        ]
        pygame.draw.polygon(surf, self.color, pts)
        pygame.draw.polygon(surf, (20, 20, 26), pts, 2)