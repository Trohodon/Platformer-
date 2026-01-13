# world/tilemap.py
import pygame
import math
import random

from core.settings import TILE_SIZE


class Tilemap:
    """
    Visual-overhaul tilemap (NO external assets).
    - Pre-renders static world layers into cached Surfaces for speed.
    - Draws nicer tiles: beveled blocks, cracks, highlights, shadows.
    - Spikes look like actual spikes.
    - Adds subtle background (stars + gradient + vignette) for depth.
    - Still provides collision rect helpers used by Player/Enemy/Bullets.

    Tile chars (from your loader maps):
      '#', 'C', 'M' -> solid
      '.' -> empty
      '^' -> spike (non-solid hazard)
      'P' -> spawn (treated as empty for visuals)
    """

    SOLIDS = {"#", "C", "M"}

    def __init__(self, grid):
        self.grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0]) if self.rows else 0

        self.width_px = self.cols * TILE_SIZE
        self.height_px = self.rows * TILE_SIZE

        # build rect list for spikes (Level uses these for damage)
        self.spikes = []
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch == "^":
                    self.spikes.append(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))

        # Cached render layers
        self._built = False
        self._bg = None           # background (screen-sized, generated per draw size)
        self._world_layer = None  # tiles + spikes, world-sized
        self._shadow_layer = None # shadow overlay, world-sized
        self._decor_layer = None  # subtle decor overlay, world-sized

        # Used to rebuild background if window size changes
        self._bg_size = None

        # Precompute for fast collision
        self._solid_rects = []
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch in self.SOLIDS:
                    self._solid_rects.append(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))

        # Build world layers once
        self._build_world_layers()

    # -------------------------------------------------------------------------
    # Collision helpers
    # -------------------------------------------------------------------------
    def is_solid_cell(self, cx, cy):
        if cx < 0 or cy < 0 or cx >= self.cols or cy >= self.rows:
            return True
        return self.grid[cy][cx] in self.SOLIDS

    def get_solid_rects_near(self, rect: pygame.Rect, pad_tiles=2):
        """
        Returns a small list of solid rects near a rect to speed up collisions.
        """
        min_cx = max(0, int(rect.left // TILE_SIZE) - pad_tiles)
        max_cx = min(self.cols - 1, int(rect.right // TILE_SIZE) + pad_tiles)
        min_cy = max(0, int(rect.top // TILE_SIZE) - pad_tiles)
        max_cy = min(self.rows - 1, int(rect.bottom // TILE_SIZE) + pad_tiles)

        out = []
        for cy in range(min_cy, max_cy + 1):
            row = self.grid[cy]
            for cx in range(min_cx, max_cx + 1):
                if row[cx] in self.SOLIDS:
                    out.append(pygame.Rect(cx * TILE_SIZE, cy * TILE_SIZE, TILE_SIZE, TILE_SIZE))
        return out

    # -------------------------------------------------------------------------
    # Rendering
    # -------------------------------------------------------------------------
    def draw(self, surf: pygame.Surface, camera):
        # Ensure background matches current screen size
        if self._bg is None or self._bg_size != surf.get_size():
            self._bg_size = surf.get_size()
            self._bg = self._build_background(self._bg_size)

        # 1) background (screen space)
        surf.blit(self._bg, (0, 0))

        # 2) world layers (world space)
        top_left = camera.apply_rect(pygame.Rect(0, 0, self.width_px, self.height_px)).topleft

        surf.blit(self._world_layer, top_left)
        surf.blit(self._decor_layer, top_left, special_flags=pygame.BLEND_RGBA_ADD)
        surf.blit(self._shadow_layer, top_left, special_flags=pygame.BLEND_RGBA_MULT)

    # -------------------------------------------------------------------------
    # Layer builders
    # -------------------------------------------------------------------------
    def _build_world_layers(self):
        self._world_layer = pygame.Surface((self.width_px, self.height_px), pygame.SRCALPHA)
        self._shadow_layer = pygame.Surface((self.width_px, self.height_px), pygame.SRCALPHA)
        self._decor_layer = pygame.Surface((self.width_px, self.height_px), pygame.SRCALPHA)

        # Base palette
        col_stone = pygame.Color(55, 60, 74)
        col_stone2 = pygame.Color(62, 68, 84)
        col_metal = pygame.Color(78, 86, 105)
        col_moss = pygame.Color(50, 78, 60)

        # Shadows / highlights
        hi = pygame.Color(160, 170, 190)
        lo = pygame.Color(18, 20, 26)

        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                wx = x * TILE_SIZE
                wy = y * TILE_SIZE
                r = pygame.Rect(wx, wy, TILE_SIZE, TILE_SIZE)

                if ch in self.SOLIDS:
                    # choose a style by char
                    if ch == "#":
                        base = col_stone
                    elif ch == "C":
                        base = col_stone2
                    else:  # "M"
                        base = col_metal

                    self._draw_block_tile(self._world_layer, x, y, r, base, hi, lo)
                    self._draw_contact_shadows(self._shadow_layer, x, y, r)

                    # subtle decor (speckles/cracks)
                    self._draw_decor(self._decor_layer, x, y, r, base)

                elif ch == "^":
                    self._draw_spike_tile(self._world_layer, x, y, r)
                    self._draw_spike_shadow(self._shadow_layer, x, y, r)

                else:
                    # empty: optional faint ambient fog glow for depth
                    pass

        self._built = True

    def _build_background(self, size):
        w, h = size
        bg = pygame.Surface((w, h), pygame.SRCALPHA)

        # gradient sky
        top = pygame.Color(10, 12, 22)
        mid = pygame.Color(18, 20, 34)
        bot = pygame.Color(28, 24, 40)

        for y in range(h):
            t = y / max(1, h - 1)
            # 2-stage gradient
            if t < 0.55:
                k = t / 0.55
                c = _lerp_color(top, mid, k)
            else:
                k = (t - 0.55) / 0.45
                c = _lerp_color(mid, bot, k)
            pygame.draw.line(bg, c, (0, y), (w, y))

        # stars (deterministic-ish)
        rng = random.Random(1337)
        star_count = int((w * h) / 14000)
        for _ in range(star_count):
            sx = rng.randrange(0, w)
            sy = rng.randrange(0, h)
            br = rng.randrange(140, 255)
            bg.set_at((sx, sy), (br, br, br, 120))

        # big soft lights
        self._draw_soft_circle(bg, int(w * 0.75), int(h * 0.25), int(min(w, h) * 0.35), (40, 60, 140, 38))
        self._draw_soft_circle(bg, int(w * 0.25), int(h * 0.65), int(min(w, h) * 0.45), (80, 40, 120, 28))

        # vignette
        vign = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            t = y / max(1, h - 1)
            edge = abs(t - 0.5) * 2.0
            a = int(110 * (edge ** 1.4))
            pygame.draw.line(vign, (0, 0, 0, a), (0, y), (w, y))
        bg.blit(vign, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

        return bg

    # -------------------------------------------------------------------------
    # Tile drawing: blocks
    # -------------------------------------------------------------------------
    def _draw_block_tile(self, surf, cx, cy, rect, base, hi, lo):
        rng = _tile_rng(cx, cy)

        # slight per-tile variation
        base2 = _tint(base, rng.randint(-6, 8))

        # fill
        pygame.draw.rect(surf, base2, rect)

        # bevel highlight/shadow
        inset = max(1, TILE_SIZE // 12)
        inner = rect.inflate(-inset * 2, -inset * 2)
        pygame.draw.rect(surf, _tint(base2, 10), inner)

        # top-left highlight edge
        pygame.draw.line(surf, _mix(hi, base2, 0.55), rect.topleft, (rect.right - 1, rect.top))
        pygame.draw.line(surf, _mix(hi, base2, 0.55), rect.topleft, (rect.left, rect.bottom - 1))

        # bottom-right shadow edge
        pygame.draw.line(surf, _mix(lo, base2, 0.55), (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1))
        pygame.draw.line(surf, _mix(lo, base2, 0.55), (rect.right - 1, rect.top), (rect.right - 1, rect.bottom - 1))

        # corners
        pygame.draw.rect(surf, (0, 0, 0, 22), rect, 1)

        # "cracks"
        if rng.random() < 0.22:
            self._draw_crack(surf, rect, rng)

        # occasional moss tint on stone tiles (looks alive)
        if rng.random() < 0.10:
            moss = pygame.Color(40, 95, 70, 35)
            pygame.draw.rect(surf, moss, rect.inflate(-inset * 2, -inset * 2), border_radius=inset)

    def _draw_crack(self, surf, rect, rng):
        pts = []
        x = rect.left + rng.randint(4, TILE_SIZE - 5)
        y = rect.top + rng.randint(4, TILE_SIZE - 5)
        pts.append((x, y))
        for _ in range(rng.randint(3, 6)):
            x += rng.randint(-10, 10)
            y += rng.randint(-10, 10)
            x = max(rect.left + 3, min(rect.right - 4, x))
            y = max(rect.top + 3, min(rect.bottom - 4, y))
            pts.append((x, y))
        pygame.draw.lines(surf, (10, 10, 12, 70), False, pts, 2)
        pygame.draw.lines(surf, (220, 220, 240, 18), False, pts, 1)

    def _draw_decor(self, surf, cx, cy, rect, base):
        rng = _tile_rng(cx, cy, salt=777)

        # speckles
        if rng.random() < 0.45:
            for _ in range(rng.randint(2, 6)):
                px = rect.left + rng.randint(2, TILE_SIZE - 3)
                py = rect.top + rng.randint(2, TILE_SIZE - 3)
                a = rng.randint(10, 30)
                surf.set_at((px, py), (base.r + 40, base.g + 40, base.b + 50, a))

        # faint glow dots
        if rng.random() < 0.10:
            px = rect.left + rng.randint(6, TILE_SIZE - 7)
            py = rect.top + rng.randint(6, TILE_SIZE - 7)
            self._draw_soft_circle(surf, px, py, rng.randint(6, 12), (120, 140, 255, 14))

    def _draw_contact_shadows(self, surf, cx, cy, rect):
        # shadow under tiles that have air below (gives depth)
        below_solid = self._cell_is_solid(cx, cy + 1)
        if not below_solid:
            h = max(3, TILE_SIZE // 6)
            sh = pygame.Surface((rect.width, h), pygame.SRCALPHA)
            for i in range(h):
                a = int(70 * (1.0 - i / max(1, h - 1)))
                pygame.draw.line(sh, (0, 0, 0, a), (0, i), (rect.width, i))
            surf.blit(sh, (rect.left, rect.bottom - 1))

        # side shadow if air to right
        right_solid = self._cell_is_solid(cx + 1, cy)
        if not right_solid:
            w = max(3, TILE_SIZE // 7)
            sh = pygame.Surface((w, rect.height), pygame.SRCALPHA)
            for i in range(w):
                a = int(55 * (1.0 - i / max(1, w - 1)))
                pygame.draw.line(sh, (0, 0, 0, a), (i, 0), (i, rect.height))
            surf.blit(sh, (rect.right - w, rect.top))

    # -------------------------------------------------------------------------
    # Tile drawing: spikes
    # -------------------------------------------------------------------------
    def _draw_spike_tile(self, surf, cx, cy, rect):
        rng = _tile_rng(cx, cy, salt=9999)

        # base plate
        plate = pygame.Color(80, 74, 95)
        pygame.draw.rect(surf, (plate.r, plate.g, plate.b, 255), rect)

        # spikes (triangles)
        spike_color = pygame.Color(190, 200, 230)
        edge = pygame.Color(40, 44, 60)

        n = 3 if TILE_SIZE < 28 else 4
        margin = max(2, TILE_SIZE // 10)
        usable = rect.width - margin * 2
        step = usable / n

        for i in range(n):
            x0 = rect.left + margin + int(i * step)
            x1 = rect.left + margin + int((i + 1) * step)
            mid = (x0 + x1) // 2

            height = int(rect.height * (0.62 + 0.10 * rng.random()))
            p1 = (x0 + 1, rect.bottom - margin)
            p2 = (x1 - 1, rect.bottom - margin)
            p3 = (mid, rect.bottom - margin - height)

            pygame.draw.polygon(surf, spike_color, [p1, p2, p3])
            pygame.draw.polygon(surf, edge, [p1, p2, p3], 2)

            # highlight edge
            pygame.draw.line(surf, (255, 255, 255, 40), p3, p1, 1)

        # border
        pygame.draw.rect(surf, (0, 0, 0, 35), rect, 1)

    def _draw_spike_shadow(self, surf, cx, cy, rect):
        # subtle shadow under the spike tips
        sh = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        for y in range(rect.height):
            t = y / max(1, rect.height - 1)
            a = int(22 * (t ** 2.2))
            pygame.draw.line(sh, (0, 0, 0, a), (0, y), (rect.width, y))
        surf.blit(sh, rect.topleft, special_flags=pygame.BLEND_RGBA_SUB)

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------
    def _cell_is_solid(self, cx, cy):
        if cx < 0 or cy < 0 or cx >= self.cols or cy >= self.rows:
            return True
        return self.grid[cy][cx] in self.SOLIDS

    def _draw_soft_circle(self, surf, cx, cy, radius, color_rgba):
        # simple radial falloff
        r = max(1, int(radius))
        tmp = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        for y in range(r * 2 + 2):
            for x in range(r * 2 + 2):
                dx = x - (r + 1)
                dy = y - (r + 1)
                d = math.sqrt(dx * dx + dy * dy)
                if d <= r:
                    k = 1.0 - (d / r)
                    a = int(color_rgba[3] * (k ** 2.2))
                    tmp.set_at((x, y), (color_rgba[0], color_rgba[1], color_rgba[2], a))
        surf.blit(tmp, (cx - r - 1, cy - r - 1), special_flags=pygame.BLEND_RGBA_ADD)


# -----------------------------------------------------------------------------
# Color helpers (pure python)
# -----------------------------------------------------------------------------
def _tile_rng(cx, cy, salt=0):
    # deterministic per tile so visuals stay consistent each run
    seed = (cx * 92837111) ^ (cy * 689287499) ^ (salt * 912367)
    return random.Random(seed & 0xFFFFFFFF)


def _clamp_u8(v):
    return 0 if v < 0 else 255 if v > 255 else int(v)


def _tint(c, delta):
    return pygame.Color(_clamp_u8(c.r + delta), _clamp_u8(c.g + delta), _clamp_u8(c.b + delta), 255)


def _mix(a, b, t):
    # t=0 -> a, t=1 -> b
    return pygame.Color(
        _clamp_u8(a.r + (b.r - a.r) * t),
        _clamp_u8(a.g + (b.g - a.g) * t),
        _clamp_u8(a.b + (b.b - a.b) * t),
        255
    )


def _lerp_color(a, b, t):
    return pygame.Color(
        _clamp_u8(a.r + (b.r - a.r) * t),
        _clamp_u8(a.g + (b.g - a.g) * t),
        _clamp_u8(a.b + (b.b - a.b) * t),
        255
    )