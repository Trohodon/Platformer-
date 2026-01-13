# entities/enemy.py
import pygame
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from core.settings import GRAVITY, MAX_FALL_SPEED, TILE_SIZE
from core.utils import clamp


SOLIDS = {"#", "C", "M"}  # must match your Tilemap solid set


class Enemy:
    """
    Enemy with (almost) the same movement kit as Player:
    - Double jump (2 jumps)
    - Dash (ground + air dashes limited)
    - Wall slide + wall jump
    - Pathfinding (BFS on tile grid) to navigate maze-like levels
    - Solid vs solid tiles via rect collision
    - Solid vs other enemies handled in Level via circle separation

    AI uses the path to set desired direction and decides when to jump/dash/walljump.
    """

    def __init__(self, x: float, y: float, radius: int = 16):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 0)
        self.radius = radius

        # health
        self.max_health = 60
        self.health = 60
        self.dead = False

        # movement tuning (enemy feels a bit "heavier" than player by default)
        self.speed = 205.0
        self.jump_speed = 760.0

        # jump kit
        self.max_jumps = 2
        self.jumps_left = self.max_jumps
        self.coyote_time = 0.10
        self.coyote_timer = 0.0
        self.jump_cd = 0.0

        # wall kit
        self.on_wall_left = False
        self.on_wall_right = False
        self.wall_slide_speed = 420.0
        self.wall_jump_x = 420.0
        self.wall_jump_y = 760.0
        self.wall_stick_time = 0.10
        self.wall_stick_timer = 0.0

        # dash kit
        self.dashing = False
        self.dash_timer = 0.0
        self.dash_time = 0.14
        self.dash_speed = 520.0
        self.dash_cooldown = 0.55
        self.dash_cd = 0.0
        self.air_dashes_max = 1
        self.air_dashes_left = self.air_dashes_max
        self._dash_dir = 1

        # state
        self.on_ground = False
        self.was_on_ground = False
        self.facing = 1

        # pathfinding
        self.repath_timer = 0.0
        self.repath_interval = 0.45
        self.path: List[Tuple[int, int]] = []
        self.path_index = 0
        self._last_player_cell: Optional[Tuple[int, int]] = None

    # ------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------
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

        # timers
        self.jump_cd = max(0.0, self.jump_cd - dt)
        self.coyote_timer = max(0.0, self.coyote_timer - dt)
        self.wall_stick_timer = max(0.0, self.wall_stick_timer - dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)

        # path
        self._pathfind_update(dt, player_rect, grid)

        # desired horizontal direction from path (fallback = chase)
        move_dir = self._desired_move_dir(player_rect)
        if move_dir != 0.0:
            self.facing = 1 if move_dir > 0 else -1
            self._dash_dir = self.facing

        # dash decision: if blocked by enemy in front OR need to cross a gap quickly
        blocked_by_enemy = self._blocked_by_enemy(move_dir, neighbors)
        gap_ahead = self._gap_ahead(move_dir, grid)
        should_dash = (blocked_by_enemy or (gap_ahead and abs(player_rect.centerx - self.pos.x) > TILE_SIZE * 2))

        if (not self.dashing) and should_dash and self.dash_cd <= 0.0:
            can_dash = self.on_ground or (self.air_dashes_left > 0)
            if can_dash and move_dir != 0.0:
                self._start_dash(move_dir)

        # movement
        if self.dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0.0:
                self.dashing = False
        else:
            self.vel.x = move_dir * self.speed

        # gravity always applies (dash clears vy only at start)
        self.vel.y += GRAVITY * dt
        self.vel.y = clamp(self.vel.y, -99999.0, MAX_FALL_SPEED)

        # apply movement + world collisions
        pre_vx = self.vel.x
        self._move_x(dt, solids)
        self._move_y(dt, solids)

        # wall flags (after movement)
        self._update_wall_flags(solids)

        # coyote / resets
        if self.on_ground:
            self.coyote_timer = self.coyote_time

        if self.on_ground and not self.was_on_ground:
            self.jumps_left = self.max_jumps
            self.air_dashes_left = self.air_dashes_max

        # wall stick & slide
        if (self.on_wall_left or self.on_wall_right) and (not self.on_ground) and self.vel.y > 0:
            self.wall_stick_timer = self.wall_stick_time

        if not self.on_ground and self.vel.y > 0:
            if (self.on_wall_left and move_dir < 0) or (self.on_wall_right and move_dir > 0):
                self.vel.y = min(self.vel.y, self.wall_slide_speed)

        # jump decisions (AI)
        blocked_by_wall = (abs(pre_vx) > 1.0 and abs(self.vel.x) < 1e-3)
        player_above = player_rect.centery < (self.pos.y - self.radius - TILE_SIZE * 0.25)
        close_x = abs(player_rect.centerx - self.pos.x) < (TILE_SIZE * 4)

        # jump if:
        # - blocked by a wall, or
        # - player is above and close, or
        # - there's a gap ahead (try to clear), or
        # - blocked by enemy and dash wasn't available
        want_jump = blocked_by_wall or (player_above and close_x) or gap_ahead or (blocked_by_enemy and (not self.dashing))

        if want_jump and self.jump_cd <= 0.0:
            # wall jump if touching wall and in air
            if (not self.on_ground) and (self.on_wall_left or self.on_wall_right) and self.wall_stick_timer > 0.0:
                self._do_wall_jump()
                self.jump_cd = 0.18
            else:
                # normal/double jump
                if (self.on_ground or self.coyote_timer > 0.0) and self.jumps_left > 0:
                    self._do_jump()
                    self.jump_cd = 0.16
                    self.coyote_timer = 0.0
                elif (not self.on_ground) and self.jumps_left > 0:
                    self._do_jump()
                    self.jump_cd = 0.16

        self.was_on_ground = self.on_ground

    # ------------------------------------------------------------
    # Dash / Jump actions
    # ------------------------------------------------------------
    def _start_dash(self, move_dir: float):
        self.dashing = True
        self.dash_timer = self.dash_time
        self.dash_cd = self.dash_cooldown

        if not self.on_ground:
            self.air_dashes_left -= 1

        self.vel.x = (1 if move_dir > 0 else -1) * self.dash_speed
        self.vel.y = 0.0

    def _do_jump(self):
        self.vel.y = -self.jump_speed
        self.on_ground = False
        self.jumps_left -= 1

    def _do_wall_jump(self):
        if self.on_wall_left:
            self.vel.x = self.wall_jump_x
        elif self.on_wall_right:
            self.vel.x = -self.wall_jump_x
        self.vel.y = -self.wall_jump_y
        self.wall_stick_timer = 0.0
        if self.jumps_left == self.max_jumps:
            self.jumps_left -= 1

    # ------------------------------------------------------------
    # Pathfinding (tile BFS)
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
        if self.path and self.path_index < len(self.path):
            tx, ty = self.path[self.path_index]
            target = self._cell_center(tx, ty)
            dx = target.x - self.pos.x

            if abs(dx) < (TILE_SIZE * 0.25) and abs(target.y - self.pos.y) < (TILE_SIZE * 0.7):
                self.path_index = min(self.path_index + 1, len(self.path))

            if abs(dx) > 6:
                return 1.0 if dx > 0 else -1.0
            return 0.0

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

        path_rev: List[Tuple[int, int]] = []
        cur: Optional[Tuple[int, int]] = (gx, gy)
        while cur is not None:
            path_rev.append(cur)
            cur = came_from.get(cur, None)

        path_rev.reverse()

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
        return ch not in SOLIDS

    def _world_to_cell(self, wx: float, wy: float) -> Tuple[int, int]:
        return int(wx // TILE_SIZE), int(wy // TILE_SIZE)

    def _cell_center(self, cx: int, cy: int) -> pygame.Vector2:
        return pygame.Vector2(cx * TILE_SIZE + TILE_SIZE * 0.5, cy * TILE_SIZE + TILE_SIZE * 0.5)

    # ------------------------------------------------------------
    # AI helpers: gap & enemy probe
    # ------------------------------------------------------------
    def _gap_ahead(self, move_dir: float, grid: List[str]) -> bool:
        if move_dir == 0.0:
            return False

        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        if rows == 0 or cols == 0:
            return False

        # look one tile ahead at foot position; if below is NOT solid, it's a gap
        foot_x = self.pos.x + (move_dir * self.radius * 1.2)
        foot_y = self.pos.y + self.radius + 2

        cx = int(foot_x // TILE_SIZE)
        cy = int(foot_y // TILE_SIZE)
        below_y = cy

        if not (0 <= cx < cols and 0 <= below_y < rows):
            return True

        ch = grid[below_y][cx]
        return ch not in SOLIDS

    def _blocked_by_enemy(self, move_dir: float, neighbors) -> bool:
        if move_dir == 0.0:
            return False

        probe = self.rect.copy()
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

    def _update_wall_flags(self, solids):
        self.on_wall_left = False
        self.on_wall_right = False
        if self.on_ground:
            return

        left_probe = self.rect.move(-1, 0)
        right_probe = self.rect.move(1, 0)

        for s in solids:
            if left_probe.colliderect(s):
                self.on_wall_left = True
            if right_probe.colliderect(s):
                self.on_wall_right = True
            if self.on_wall_left and self.on_wall_right:
                break

    # ------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------
    def draw(self, surf: pygame.Surface, camera):
        if self.dead:
            return

        rr_screen = camera.apply(self.rect)
        cx, cy = rr_screen.center

        pygame.draw.circle(surf, (240, 120, 120), (cx, cy), self.radius)

        bar_w = 40
        bar_h = 6
        pct = max(0.0, min(1.0, self.health / self.max_health))
        fill_w = int(bar_w * pct)

        bx = cx - bar_w // 2
        by = cy - self.radius - 14

        pygame.draw.rect(surf, (40, 40, 55), (bx, by, bar_w, bar_h))
        pygame.draw.rect(surf, (220, 80, 80), (bx, by, fill_w, bar_h))
        pygame.draw.rect(surf, (230, 230, 240), (bx, by, bar_w, bar_h), 1)