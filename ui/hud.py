# ui/hud.py
import pygame
from core.settings import HUD_COLOR


class HUD:
    def __init__(self, assets):
        self.font = assets.font_small

    def draw(self, surf: pygame.Surface, level):
        p = level.player

        x, y = 10, 10
        w, h = 220, 18
        pct = 0.0 if p.max_health <= 0 else (p.health / p.max_health)
        fill_w = int(w * max(0.0, min(1.0, pct)))

        pygame.draw.rect(surf, (40, 40, 55), (x, y, w, h))
        pygame.draw.rect(surf, (80, 220, 120), (x, y, fill_w, h))
        pygame.draw.rect(surf, HUD_COLOR, (x, y, w, h), 2)

        img = self.font.render(f"HP: {p.health}/{p.max_health}", True, HUD_COLOR)
        surf.blit(img, (x, y + 24))

        img2 = self.font.render("Shoot: J/K or Left Click", True, (180, 180, 190))
        surf.blit(img2, (x, y + 48))