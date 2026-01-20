# ui/hud.py
import pygame
from world.powerup_defs import POWERUPS


class HUD:
    def __init__(self, font_size: int = 18):
        pygame.font.init()
        self.font = pygame.font.SysFont("consolas", font_size)

    def draw(self, surf: pygame.Surface, level):
        # health bar
        p = level.player
        w = 240
        h = 16
        x = 14
        y = 12

        pct = 0.0 if p.max_health <= 0 else max(0.0, min(1.0, p.health / p.max_health))
        fill = int(w * pct)

        pygame.draw.rect(surf, (40, 40, 55), (x, y, w, h))
        pygame.draw.rect(surf, (80, 210, 120), (x, y, fill, h))
        pygame.draw.rect(surf, (230, 230, 240), (x, y, w, h), 2)

        txt = self.font.render(f"HP {p.health}/{p.max_health}", True, (235, 235, 245))
        surf.blit(txt, (x, y + 20))

        # wave
        txt2 = self.font.render(f"WAVE {level.waves.wave_number}", True, (235, 235, 245))
        surf.blit(txt2, (x + 260, y))

        # show stacks summary (top 6)
        items = [(k, v) for k, v in p.abilities.stacks.items() if v > 0]
        items.sort(key=lambda kv: (-kv[1], kv[0]))
        items = items[:6]
        yy = y + 44
        for pid, stacks in items:
            name = POWERUPS.get(pid, {}).get("name", pid)
            t = self.font.render(f"{name} x{stacks}", True, (210, 210, 225))
            surf.blit(t, (x, yy))
            yy += 18