# entities/enemy.py
import pygame
import random


class Enemy:
    """
    Performance-friendly enemy:
    - Uses FlowField direction instead of per-enemy pathfinding
    - Has player-like abilities: jump, dash, wall-slide-ish behavior
    - Solid circle body; resolves collisions with nearby enemies (handled in Level via buckets)
    """

    def __init__(self, x: float, y: float, radius: int = 16, kind: str = "grunt"):
        self.kind = kind
        self.radius = int(radius)

        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 0)

        self.on_ground = False
        self.facing = 1

        self.max_health = 60
        self.health = self.max_health
        self.dead = False

        # movement feel (similar to player)
        self.run_speed = 210.0
        self.jump_speed = 780.0
        self.gravity = 2200.0
        self.max_fall = 1150.0

        # dash
        self.dashing = False
        self.dash_timer = 0.0
        self.dash_cd = random.uniform(0.15, 0.35)
        self.dash_time = 0.10
        self.dash_speed = 620.0
        self.air_dashes_left = 1

        # jump control
        self.jumps_left = 1
        self.coyote = 0.0

        # wall
        self.wall_lock = 0.0
        self.wall_dir = 0

        # brain
        self._think = random.uniform(0.0, 0.25)
        self._jump_intent = 0.0

        self.color = (120, 200, 255) if kind == "grunt" else (200, 200, 200)

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.pos.x - self.radius),
            int(self.pos.y - self.radius),
            self.radius * 2,
            self.radius * 2
        )

    def take_damage(self, amount: int):
        if self.dead:
            return
        self.health -= int(amount)
        if self.health <= 0:
            self.dead = True

    def update(self, dt: float, player_rect: pygame.Rect, solids, spikes, flow_dir: pygame.Vector2, enemies_near):
        if self.dead:
            return

        # dt safety to avoid spiral-of-death
        if dt > 1.0 / 30.0:
            dt = 1.0 / 30.0

        # timers
        if self.dash_cd > 0.0:
            self.dash_cd = max(0.0, self.dash_cd - dt)
        if self.wall_lock > 0.0:
            self.wall_lock = max(0.0, self.wall_lock - dt)

        # ground/coyote bookkeeping
        if self.on_ground:
            self.coyote = 0.10
        else:
            self.coyote = max(0.0, self.coyote - dt)

        # think (coarse)
        self._think -= dt
        if self._think <= 0.0:
            self._think = 0.10 + random.random() * 0.12

            # choose a desired move direction from flow
            if flow_dir.length_squared() > 0:
                self.facing = 1 if flow_dir.x >= 0 else -1
            else:
                # fallback: direct chase
                self.facing = 1 if player_rect.centerx >= self.rect.centerx else -1

            # decide if we should jump soon (obstacle / spike / crowd)
            self._jump_intent = 0.14 if random.random() < 0.35 else 0.0

        # desired movement
        move_x = 0
        if flow_dir.length_squared() > 0:
            if flow_dir.x > 0.15:
                move_x = 1
            elif flow_dir.x < -0.15:
                move_x = -1
        else:
            move_x = 1 if player_rect.centerx > self.rect.centerx else -1

        if move_x != 0:
            self.facing = 1 if move_x > 0 else -1

        # wall detection (light)
        if self.wall_lock <= 0.0 and (not self.on_ground):
            self.wall_dir = self._detect_wall(solids)
        else:
            self.wall_dir = 0

        # dash decision:
        # - if stuck behind another enemy or pushing into wall, dash to "climb over"
        if (not self.dashing) and self.dash_cd <= 0.0:
            if self._should_dash(enemies_near, solids, move_x):
                can_dash = self.on_ground or self.air_dashes_left > 0
                if can_dash:
                    self.dashing = True
                    self.dash_timer = self.dash_time
                    self.vel.y = 0.0
                    self.vel.x = self.facing * self.dash_speed
                    self.dash_cd = 0.25 + random.random() * 0.45
                    if not self.on_ground:
                        self.air_dashes_left -= 1

        # jump decision:
        # - jump if spikes ahead or obstacle ahead or jump_intent timer
        if self._jump_intent > 0.0:
            self._jump_intent = max(0.0, self._jump_intent - dt)
            if self._can_jump() and self._should_jump(solids, spikes, move_x):
                self._do_jump()
                self._jump_intent = 0.0

        # physics
        if self.dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0.0:
                self.dashing = False
        else:
            # horizontal accel
            target = move_x * self.run_speed
            accel = 3600.0 if self.on_ground else 2200.0
            diff = target - self.vel.x
            step = accel * dt
            if diff > step:
                diff = step
            elif diff < -step:
                diff = -step
            self.vel.x += diff

            # gravity
            self.vel.y = min(self.max_fall, self.vel.y + self.gravity * dt)

        # move + collide
        self._move_and_collide(dt, solids)

        # spike damage (same logic as player) — no i-frames for now
        for sp in spikes:
            if self.rect.colliderect(sp):
                self.take_damage(30)
                break

        # reset stocks
        if self.on_ground:
            self.jumps_left = 1
            self.air_dashes_left = 1

    def _can_jump(self) -> bool:
        return self.on_ground or (self.coyote > 0.0) or (self.jumps_left > 0)

    def _do_jump(self):
        if not (self.on_ground or self.coyote > 0.0):
            self.jumps_left -= 1
        self.vel.y = -self.jump_speed
        self.on_ground = False
        self.coyote = 0.0

    def _should_jump(self, solids, spikes, move_x: int) -> bool:
        r = self.rect

        # Spike ahead?
        ahead = r.move(move_x * (self.radius + 6), 0)
        ahead_in_front = ahead.inflate(10, 10)
        for sp in spikes:
            if ahead_in_front.colliderect(sp):
                return True

        # Wall/step ahead?
        foot = pygame.Rect(r.centerx + move_x * (self.radius + 6), r.bottom - 10, 6, 10)
        head = pygame.Rect(r.centerx + move_x * (self.radius + 6), r.top + 6, 6, r.height - 20)

        hit_foot = False
        hit_head = False
        for s in solids:
            if foot.colliderect(s):
                hit_foot = True
            if head.colliderect(s):
                hit_head = True
            if hit_foot or hit_head:
                break

        # If blocked at feet or head, try jump
        if hit_foot or hit_head:
            return True

        return False

    def _should_dash(self, enemies_near, solids, move_x: int) -> bool:
        # if pushing into a wall, dash to "climb"
        if self.wall_dir != 0 and ((move_x < 0 and self.wall_dir < 0) or (move_x > 0 and self.wall_dir > 0)):
            return True

        # if crowded in front, dash sometimes
        r = self.rect
        front = r.move(move_x * (self.radius + 10), 0)
        cnt = 0
        for e in enemies_near:
            if e is self or getattr(e, "dead", False):
                continue
            if front.colliderect(e.rect):
                cnt += 1
                if cnt >= 2:
                    return True

        return False

    def _detect_wall(self, solids) -> int:
        r = self.rect
        left_probe = pygame.Rect(r.left - 1, r.top + 2, 1, r.height - 4)
        right_probe = pygame.Rect(r.right, r.top + 2, 1, r.height - 4)

        hit_left = False
        hit_right = False
        for s in solids:
            if left_probe.colliderect(s):
                hit_left = True
            if right_probe.colliderect(s):
                hit_right = True
            if hit_left and hit_right:
                break

        if hit_left and not hit_right:
            return -1
        if hit_right and not hit_left:
            return +1
        return 0

    def _move_and_collide(self, dt: float, solids):
        # X
        self.pos.x += self.vel.x * dt
        r = self.rect
        r.x = int(self.pos.x - self.radius)

        for s in solids:
            if r.colliderect(s):
                if self.vel.x > 0:
                    r.right = s.left
                elif self.vel.x < 0:
                    r.left = s.right
                self.pos.x = r.centerx
                self.vel.x = 0.0

        # Y
        self.pos.y += self.vel.y * dt
        r.y = int(self.pos.y - self.radius)

        self.on_ground = False
        for s in solids:
            if r.colliderect(s):
                if self.vel.y > 0:
                    r.bottom = s.top
                    self.on_ground = True
                elif self.vel.y < 0:
                    r.top = s.bottom
                self.pos.y = r.centery
                self.vel.y = 0.0

    def draw(self, surf: pygame.Surface, camera):
        rr = camera.apply(self.rect)
        cx, cy = rr.center

        pygame.draw.circle(surf, self.color, (cx, cy), self.radius)
        pygame.draw.circle(surf, (20, 20, 26), (cx, cy), self.radius, 2)

        # health bar
        if self.max_health > 0:
            pct = max(0.0, min(1.0, self.health / self.max_health))
            bw = self.radius * 2
            bh = 5
            x = rr.left
            y = rr.top - 10
            pygame.draw.rect(surf, (40, 40, 55), (x, y, bw, bh))
            pygame.draw.rect(surf, (240, 120, 120), (x, y, int(bw * pct), bh))
            pygame.draw.rect(surf, (230, 230, 240), (x, y, bw, bh), 1)