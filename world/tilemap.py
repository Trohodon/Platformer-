# world/tilemap.py
import pygame
import random
from core.settings import TILE_SIZE

SOLID_CHARS = {"#", "C", "M"}


class Tilemap:
    """
    Visual upgrade tilemap:
    - Greedy-merged solid rectangles for faster collision + cleaner draw
    - Pretty tiles: subtle gradients, outlines, cracks, top highlights
    - Spikes drawn as triangles (not boxes)
    - C and M get distinct "material" looks
    - Optional parallax background grid + vignette (no assets)
    """

    def __init__(self, grid):
        self.grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0]) if self.rows else 0

        self.solids = []          # merged collision rects
        self.spikes = []          # spike rects for collision
        self.spike_tiles = []     # spike tile coords for draw

        # render caches
        self._solid_surface = None
        self._spike_surface = None
        self._bg_surface = None

        self._build()

    # ------------------------------------------------------------
    # Build: merge solids + collect spikes + pre-render
    # ------------------------------------------------------------
    def _build(self):
        self.solids.clear()
        self.spikes.clear()
        self.spike_tiles.clear()

        if self.rows == 0 or self.cols == 0:
            return

        solid_grid = [[False] * self.cols for _ in range(self.rows)]

        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch in SOLID_CHARS:
                    solid_grid[y][x] = True
                elif ch == "^":
                    r = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    spike = pygame.Rect(
                        r.x + TILE_SIZE // 6,
                        r.y + TILE_SIZE // 3,
                        TILE_SIZE * 2 // 3,
                        TILE_SIZE * 2 // 3
                    )
                    self.spikes.append(spike)
                    self.spike_tiles.append((x, y))

        self.solids = self._greedy_merge_solids(solid_grid)

        self._pre_render()

    def _greedy_merge_solids(self, solid_grid):
        visited = [[False] * self.cols for _ in range(self.rows)]
        merged = []

        for y in range(self.rows):
            x = 0
            while x < self.cols:
                if visited[y][x] or not solid_grid[y][x]:
                    x += 1
                    continue

                # find max width
                w = 1
                while x + w < self.cols and solid_grid[y][x + w] and not visited[y][x + w]:
                    w += 1

                # find max height for that width
                h = 1
                done = False
                while y + h < self.rows and not done:
                    for xx in range(x, x + w):
                        if not solid_grid[y + h][xx] or visited[y + h][xx]:
                            done = True
                            break
                    if not done:
                        h += 1

                # mark visited
                for yy in range(y, y + h):
                    for xx in range(x, x + w):
                        visited[yy][xx] = True

                merged.append(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, w * TILE_SIZE, h * TILE_SIZE))
                x += w

        return merged

    # ------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------
    def _pre_render(self):
        w = self.cols * TILE_SIZE
        h = self.rows * TILE_SIZE

        if w <= 0 or h <= 0:
            return

        self._bg_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        self._solid_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        self._spike_surface = pygame.Surface((w, h), pygame.SRCALPHA)

        self._draw_background(self._bg_surface)
        self._draw_solids(self._solid_surface)
        self._draw_spikes(self._spike_surface)

    def _draw_background(self, surf):
        # soft dark base
        surf.fill((14, 16, 24, 255))

        # faint parallax grid pattern (baked at full res; camera provides motion)
        step = TILE_SIZE * 2
        for x in range(0, surf.get_width(), step):
            pygame.draw.line(surf, (22, 25, 38, 255), (x, 0), (x, surf.get_height()), 1)
        for y in range(0, surf.get_height(), step):
            pygame.draw.line(surf, (22, 25, 38, 255), (0, y), (surf.get_width(), y), 1)

        # vignette
        v = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        w, h = surf.get_size()
        pygame.draw.rect(v, (0, 0, 0, 0), (0, 0, w, h))
        pygame.draw.rect(v, (0, 0, 0, 85), (0, 0, w, h), border_radius=18)
        surf.blit(v, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

    def _tile_material_color(self, ch):
        if ch == "#":
            return (70, 78, 95)
        if ch == "C":  # "castle/brick"
            return (92, 78, 74)
        if ch == "M":  # "metal"
            return (76, 84, 92)
        return (70, 78, 95)

    def _draw_solids(self, surf):
        rng = random.Random(1337)

        # draw per-tile details so it looks like tiles, but keep collisions merged
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch not in SOLID_CHARS:
                    continue

                base = self._tile_material_color(ch)
                r = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

                # base fill
                pygame.draw.rect(surf, base, r)

                # subtle gradient highlight (top)
                hl = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                pygame.draw.rect(hl, (255, 255, 255, 18), (0, 0, TILE_SIZE, max(2, TILE_SIZE // 4)))
                surf.blit(hl, r.topleft)

                # outline
                pygame.draw.rect(surf, (28, 32, 44), r, 1)

                # cracks / texture
                if ch == "#":
                    if rng.random() < 0.22:
                        self._draw_crack(surf, r, rng, (45, 50, 64))
                elif ch == "C":
                    # brick lines
                    if y % 2 == 0:
                        pygame.draw.line(surf, (58, 50, 46), (r.x, r.centery), (r.right, r.centery), 1)
                    if x % 3 == 0:
                        pygame.draw.line(surf, (58, 50, 46), (r.centerx, r.y), (r.centerx, r.bottom), 1)
                elif ch == "M":
                    # rivets
                    if rng.random() < 0.20:
                        self._draw_rivet(surf, r, rng)

                # top edge glow if exposed to air above (makes platforms pop)
                if y > 0 and self.grid[y - 1][x] not in SOLID_CHARS:
                    pygame.draw.line(surf, (210, 220, 255), (r.x + 1, r.y + 1), (r.right - 2, r.y + 1), 1)

        # optional: draw merged blocks faint shadow for depth
        for block in self.solids:
            shadow = pygame.Surface((block.w, block.h), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0, 0, 0, 40), (0, 0, block.w, block.h))
            surf.blit(shadow, (block.x + 2, block.y + 2))

    def _draw_crack(self, surf, r, rng, color):
        points = []
        x = r.x + rng.randint(2, TILE_SIZE - 3)
        y = r.y + rng.randint(2, TILE_SIZE - 3)
        points.append((x, y))
        for _ in range(rng.randint(2, 5)):
            x += rng.randint(-8, 8)
            y += rng.randint(-8, 8)
            x = max(r.x + 2, min(r.right - 3, x))
            y = max(r.y + 2, min(r.bottom - 3, y))
            points.append((x, y))
        if len(points) >= 2:
            pygame.draw.lines(surf, color, False, points, 1)

    def _draw_rivet(self, surf, r, rng):
        cx = r.x + rng.randint(6, TILE_SIZE - 7)
        cy = r.y + rng.randint(6, TILE_SIZE - 7)
        pygame.draw.circle(surf, (40, 45, 55), (cx, cy), 3)
        pygame.draw.circle(surf, (160, 170, 180), (cx, cy), 2)
        pygame.draw.circle(surf, (255, 255, 255), (cx - 1, cy - 1), 1)

    def _draw_spikes(self, surf):
        # draw triangle spikes for each spike tile
        for (x, y) in self.spike_tiles:
            r = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

            # three spikes per tile
            spikes = 3
            pad = 3
            w = (TILE_SIZE - pad * 2) // spikes
            base_y = r.bottom - 3

            for i in range(spikes):
                sx = r.x + pad + i * w
                pts = [
                    (sx, base_y),
                    (sx + w, base_y),
                    (sx + w // 2, r.y + TILE_SIZE // 3),
                ]
                pygame.draw.polygon(surf, (210, 70, 70), pts)
                pygame.draw.polygon(surf, (90, 25, 25), pts, 1)

            # slight glow
            glow = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(glow, (255, 80, 80, 18), (0, TILE_SIZE // 2, TILE_SIZE, TILE_SIZE // 2))
            surf.blit(glow, r.topleft)

    # ------------------------------------------------------------
    # API
    # ------------------------------------------------------------
    def draw(self, surf: pygame.Surface, camera):
        if self._bg_surface is not None:
            surf.blit(self._bg_surface, camera.apply(pygame.Rect(0, 0, self._bg_surface.get_width(), self._bg_surface.get_height())))

        if self._solid_surface is not None:
            surf.blit(self._solid_surface, camera.apply(pygame.Rect(0, 0, self._solid_surface.get_width(), self._solid_surface.get_height())))

        if self._spike_surface is not None:
            surf.blit(self._spike_surface, camera.apply(pygame.Rect(0, 0, self._spike_surface.get_width(), self._spike_surface.get_height())))

    def get_solid_rects_near(self, rect: pygame.Rect):
        # keep it simple for now; merged list is already much smaller than per-tile
        return self.solids