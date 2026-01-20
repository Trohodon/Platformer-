# ui/hud.py
import pygame
from world.powerup_defs import POWERUPS


class HUD:
    def __init__(self, font_size: int = 18):
        pygame.font.init()
        try:
            fs = int(font_size)
        except Exception:
            fs = 18
        fs = max(10, min(48, fs))
        self.font = pygame.font.SysFont("consolas", fs)

    def draw(self, surf: pygame.Surface, level, fps: float = 0.0):
        p = level.player

        # HP bar
        w = 240
        h = 16
        x = 14
        y = 12

        max_hp = max(1, int(getattr(p, "max_health", 100)))
        hp = int(getattr(p, "health", max_hp))
        pct = max(0.0, min(1.0, hp / max_hp))
        fill = int(w * pct)

        pygame.draw.rect(surf, (40, 40, 55), (x, y, w, h))
        pygame.draw.rect(surf, (80, 210, 120), (x, y, fill, h))
        pygame.draw.rect(surf, (230, 230, 240), (x, y, w, h), 2)

        surf.blit(self.font.render(f"HP {hp}/{max_hp}", True, (235, 235, 245)), (x, y + 20))

        # Wave + perf
        wave_num = getattr(level.waves, "wave_number", 1)
        enemies = len(getattr(level, "enemies", []))
        bullets = len(getattr(level, "bullets", []))

        surf.blit(self.font.render(f"WAVE {wave_num}", True, (235, 235, 245)), (x + 260, y))
        surf.blit(self.font.render(f"FPS {fps:.0f}", True, (235, 235, 245)), (x + 260, y + 20))
        surf.blit(self.font.render(f"E {enemies}  B {bullets}", True, (210, 210, 225)), (x + 260, y + 40))

        # powerup stacks
        stacks = {}
        try:
            stacks = dict(getattr(p, "abilities").stacks)
        except Exception:
            stacks = {}

        items = [(k, int(v)) for k, v in stacks.items() if int(v) > 0]
        items.sort(key=lambda kv: (-kv[1], kv[0]))
        items = items[:8]

        yy = y + 44
        for pid, count in items:
            name = POWERUPS.get(pid, {}).get("name", pid)
            surf.blit(self.font.render(f"{name} x{count}", True, (210, 210, 225)), (x, yy))
            yy += 18