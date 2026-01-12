# ui/hud.py
import pygame
from core.settings import HUD_COLOR

class HUD:
    def __init__(self, assets):
        self.font = assets.font_small

    def draw(self, surf: pygame.Surface, level):
        p = level.player

        # Health bar
        x, y = 10, 10
        w, h = 220, 18
        pct = 0.0 if p.max_health <= 0 else (p.health / p.max_health)
        fill_w = int(w * max(0.0, min(1.0, pct)))

        pygame.draw.rect(surf, (40, 40, 55), (x, y, w, h))          # background
        pygame.draw.rect(surf, (80, 220, 120), (x, y, fill_w, h))   # fill
        pygame.draw.rect(surf, HUD_COLOR, (x, y, w, h), 2)          # border

        # Text
        text = f"HP: {p.health}/{p.max_health}"
        img = self.font.render(text, True, HUD_COLOR)
        surf.blit(img, (x, y + 24))