# ui/hud.py
import pygame
from world.powerup_defs import POWERUPS


class HUD:
    """
    Robust HUD:
    - Handles accidental HUD(assets) calls by coercing font_size safely
    - Fixes Level.player bug (must be level.player)
    - Shows HP bar, wave, and top powerup stacks
    """

    def __init__(self, font_size: int = 18):
        pygame.font.init()

        # If caller accidentally does HUD(assets) or HUD(something_not_int),
        # force a sane default instead of crashing.
        try:
            fs = int(font_size)
        except Exception:
            fs = 18

        fs = max(10, min(48, fs))
        self.font = pygame.font.SysFont("consolas", fs)

    def draw(self, surf: pygame.Surface, level):
        p = level.player  # FIX: was Level.player

        # -------------------------
        # Health Bar
        # -------------------------
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

        txt = self.font.render(f"HP {hp}/{max_hp}", True, (235, 235, 245))
        surf.blit(txt, (x, y + 20))

        # -------------------------
        # Wave
        # -------------------------
        wave_num = 1
        try:
            wave_num = int(level.waves.wave_number)
        except Exception:
            pass

        txt2 = self.font.render(f"WAVE {wave_num}", True, (235, 235, 245))
        surf.blit(txt2, (x + 260, y))

        # -------------------------
        # Powerup stacks (top 8)
        # -------------------------
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
            t = self.font.render(f"{name} x{count}", True, (210, 210, 225))
            surf.blit(t, (x, yy))
            yy += 18