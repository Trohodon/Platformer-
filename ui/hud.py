# ui/hud.py
import pygame
from core.settings import HUD_COLOR

class HUD:
    def __init__(self, assets):
        self.font = assets.font_small

    def draw(self, surf: pygame.Surface, level):
        p = level.player
        text = f"pos=({p.rect.x},{p.rect.y})  vel=({int(p.vel.x)},{int(p.vel.y)})  grounded={p.on_ground}"
        img = self.font.render(text, True, HUD_COLOR)
        surf.blit(img, (10, 10))