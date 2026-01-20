# entities/bullet.py
import pygame


class Bullet:
    def __init__(self, x: float, y: float, vx: float, vy: float, damage: int = 20):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(vx, vy)
        self.damage = int(damage)

        self.radius = 4
        self.alive = True
        self.life = 1.25  # seconds

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.pos.x - self.radius),
            int(self.pos.y - self.radius),
            self.radius * 2,
            self.radius * 2
        )

    def update(self, dt: float, solids):
        if not self.alive:
            return

        self.life -= dt
        if self.life <= 0.0:
            self.alive = False
            return

        self.pos += self.vel * dt

        r = self.rect
        for s in solids:
            if r.colliderect(s):
                self.alive = False
                return

    def draw(self, surf: pygame.Surface, camera):
        if not self.alive:
            return

        rr = camera.apply(self.rect)
        cx, cy = rr.center
        pygame.draw.circle(surf, (220, 220, 120), (cx, cy), self.radius)