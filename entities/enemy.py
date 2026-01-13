# entities/enemy.py
import pygame
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from core.settings import GRAVITY, MAX_FALL_SPEED, TILE_SIZE
from core.utils import clamp


WALKABLE = {".", "P", "^"}   # enemies can walk through spike tiles (damage handled elsewhere)
SOLIDS = {"#", "C", "M"}     # same as tilemap solids


class Enemy:
    """
    Solid circle enemy with:
    - Tile-based BFS pathfinding through maze-like levels (replans periodically)
    - Dash-to-climb behavior when blocked by other enemies
    - Standard rect-vs-tile collision
    Enemy solidity vs enemy is resolved in Level (pairwise circle separation).
    """

    def __init__(self, x: float, y: float, radius: int = 16):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 0)
        self.radius = radius

        self.max_health = 60
        self.health = 60
        self.dead = False

        self.speed = 210.0
        self.jump_speed = 760.0

        # dash to "climb" over crowds
        self.dashing = False
        self.dash_timer = 0.0
        self.dash_cd = 0.0
        self.dash_time = 0.14
        self.dash_speed = 520.0
        self.dash_hop = 260.0
        self.dash_cooldown = 0.55

        self.on_ground = False
        self.jump_cd = 0.0

        # pathfinding
        self.repath_timer = 0.0
        self.repath_interval = 0.45
        self.path: List[Tuple[int, int]] = []
        self.path_index = 0
        self._last_player_cell: Optional[Tuple[int, int]] = None

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.pos.x - self.radius),
            int(self.pos.y - self.radius),
            self.radius * 2,
            self.radius * 2
        )

    def take_damage(self, dmg: int):
        if self.dead:
            return
        self.health -= int(dmg)
        if self.health <= 0:
            self.dead = True

    # ------------------------------------------------------------
    # Update
    # ------------------------------------------------------------
    def update(self, dt: float, player_rect: pygame.Rect, solids, grid: List[str], neighbors):
        if self.dead:
            return

        self.jump_cd = max(0.0, self.jump_cd - dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)

        # --- pathfind ---
        self._pathfind_update(dt, player_rect, grid)

        # choose target direction from path (fallback = direct chase)
        move_dir = self._desired_move_dir(player_rect)

        # --- dash if blocked by enemy in front (to climb over) ---
        blocked_by_enemy = self._blocked_by_enemy(move_dir, neighbors)

        if (not self.dashing) and self.on_ground and (self.dash_cd <= 0.0) and blocked_by_enemy:
            # quick burst + small hop so they "climb" instead of blob
            self.dashing = True
            self.dash_timer = self.dash_time
            self.dash_cd = self.dash_cooldown
            self.vel.x = move_dir * self.dash_speed
            self.vel.y = -self.dash_hop

        # --- movement + physics ---
        if self.dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0.0:
                self.dashing = False
        else:
            self.vel.x = move_dir * self.speed

        self.vel.y += GRAVITY * dt
        self.vel.y = clamp(self.vel.y, -99999.0, MAX_FALL_SPEED)

        pre_vx = self.vel.x
        self._move_x(dt, solids)
        self._move_y(dt, solids)

        # --- jump if blocked by wall while grounded (maze stairs/steps) ---
        blocked_by_wall = (abs(pre_vx) > 1.0 and abs(self.vel.x) < 1e-3)
        if self.on_ground and (not self.dashing) and self.jump_cd <= 0.0 and blocked_by_wall:
            self.vel.y = -self.jump_speed
            self.on_ground = False
            self.jump_cd = 0.25

    # ------------------------------------------------------------
    # Pathfinding
    # ------------------------------------------------------------
    def _pathfind_update(self, dt: float, player_rect: pygame.Rect, grid: List[str]):
        self.repath_timer -= dt
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        if rows == 0 or cols == 0:
            self.path = []
            self.path_index = 0
            return

        player_cell = self._world_to_cell(player_rect.centerx, player_rect.centery)
        enemy_cell = self._world_to_cell(self.pos.x, self.pos.y)

        # force replan if player moved to a new tile or timer elapsed or path invalid
        need_repath = False
        if self._last_player_cell != player_cell:
            need_repath = True
        if self.repath_timer <= 0.0:
            need_repath = True
        if self.path_index >= len(self.path):
            need_repath = True

        if need_repath:
            self.repath_timer = self.repath_interval
            self._last_player_cell = player_cell

            path = self._bfs_path(grid, enemy_cell, player_cell)
            if path is None:
                self.path = []
                self.path_index = 0
            else:
                self.path = path
                self.path_index = 0

    def _desired_move_dir(self, player_rect: pygame.Rect) -> float:
        # follow the next cell center in the path
        if self.path and self.path_index < len(self.path):
            tx, ty = self.path[self.path_index]
            target = self._cell_center(tx, ty)
            dx = target.x - self.pos.x

            # advance to next waypoint if close
            if abs(dx) < (TILE_SIZE * 0.25) and abs(target.y - self.pos.y) < (TILE_SIZE * 0.6):
                self.path_index = min(self.path_index + 1, len(self.path))
            if abs(dx) > 6:
                return 1.0 if dx > 0 else -1.0
            return 0.0

        # fallback: direct chase
        dx = player_rect.centerx - self.pos.x
        if abs(dx) > 6:
            return 1.0 if dx > 0 else -1.0
        return 0.0

    def _bfs_path(self, grid: List[str], start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        rows = len(grid)
        cols = len(grid[0]) if rows else 0

        sx, sy = start
        gx, gy = goal

        if not (0 <= sx < cols and 0 <= sy < rows):
            return None
        if not (0 <= gx < cols and 0 <= gy < rows):
            return None

        # if goal is inside a wall, try a nearby walkable cell
        if not self._is_walkable(grid, gx, gy):
            found = self._nearest_walkable(grid, gx, gy, radius=3)
            if found is None:
                return None
            gx, gy = found

        q = deque()  # type: Deque[Tuple[int, int]]
        q.append((sx, sy))

        came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {}
        came_from[(sx, sy)] = None

        dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))

        while q:
            x, y = q.popleft()
            if (x, y) == (gx, gy):
                break

            for dx, dy in dirs:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < cols and 0 <= ny < rows):
                    continue
                if (nx, ny) in came_from:
                    continue
                if not self._is_walkable(grid, nx, ny):
                    continue
                came_from[(nx, ny)] = (x, y)
                q.append((nx, ny))

        if (gx, gy) not in came_from:
            return None

        # reconstruct
        path_rev: List[Tuple[int, int]] = []
        cur: Optional[Tuple[int, int]] = (gx, gy)
        while cur is not None:
            path_rev.append(cur)
            cur = came_from.get(cur, None)

        path_rev.reverse()

        # skip the first cell if it's our current cell
        if path_rev and path_rev[0] == (sx, sy):
            path_rev = path_rev[1:]

        return path_rev

    def _nearest_walkable(self, grid: List[str], cx: int, cy: int, radius: int = 3) -> Optional[Tuple[int, int]]:
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        best = None
        best_d2 = 10**9
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                x, y = cx + dx, cy + dy
                if 0 <= x < cols and 0 <= y < rows and self._is_walkable(grid, x, y):
                    d2 = dx * dx + dy * dy
                    if d2 < best_d2:
                        best_d2 = d2
                        best = (x, y)
        return best

    def _is_walkable(self, grid: List[str], x: int, y: int) -> bool:
        ch = grid[y][x]
        if ch in SOLIDS:
            return False
        # treat everything else as walkable floor-space
        return True

    def _world_to_cell(self, wx: float, wy: float) -> Tuple[int, int]:
        return int(wx // TILE_SIZE), int(wy // TILE_SIZE)

    def _cell_center(self, cx: int, cy: int) -> pygame.Vector2:
        return pygame.Vector2(cx * TILE_SIZE + TILE_SIZE * 0.5, cy * TILE_SIZE + TILE_SIZE * 0.5)

    # ------------------------------------------------------------
    # Enemy blocking probe
    # ------------------------------------------------------------
    def _blocked_by_enemy(self, move_dir: float, neighbors) -> bool:
        if move_dir == 0.0:
            return False

        my_r = self.rect
        probe = my_r.copy()
        probe.x += int(move_dir * (self.radius + 8))
        probe.y += int(self.radius * 0.25)
        probe.height = int(self.radius * 1.2)

        for other in neighbors:
            if other is self or other.dead:
                continue
            if probe.colliderect(other.rect):
                return True
        return False

    # ------------------------------------------------------------
    # Tile collision
    # ------------------------------------------------------------
    def _move_x(self, dt: float, solids):
        self.pos.x += self.vel.x * dt
        r = self.rect
        for s in solids:
            if r.colliderect(s):
                if self.vel.x > 0:
                    self.pos.x = s.left - self.radius
                elif self.vel.x < 0:
                    self.pos.x = s.right + self.radius
                self.vel.x = 0.0
                r = self.rect

    def _move_y(self, dt: float, solids):
        self.pos.y += self.vel.y * dt
        self.on_ground = False
        r = self.rect
        for s in solids:
            if r.colliderect(s):
                if self.vel.y > 0:
                    self.pos.y = s.top - self.radius
                    self.vel.y = 0.0
                    self.on_ground = True
                elif self.vel.y < 0:
                    self.pos.y = s.bottom + self.radius
                    self.vel.y = 0.0
                r = self.rect

    # ------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------
    def draw(self, surf: pygame.Surface, camera):
        if self.dead:
            return

        rr_screen = camera.apply(self.rect)
        cx, cy = rr_screen.center

        pygame.draw.circle(surf, (240, 120, 120), (cx, cy), self.radius)

        # health bar
        bar_w = 40
        bar_h = 6
        pct = max(0.0, min(1.0, self.health / self.max_health))
        fill_w = int(bar_w * pct)

        bx = cx - bar_w // 2
        by = cy - self.radius - 14

        pygame.draw.rect(surf, (40, 40, 55), (bx, by, bar_w, bar_h))
        pygame.draw.rect(surf, (220, 80, 80), (bx, by, fill_w, bar_h))
        pygame.draw.rect(surf, (230, 230, 240), (bx, by, bar_w, bar_h), 1)