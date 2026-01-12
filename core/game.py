# core/game.py
import pygame

from core.settings import TITLE, WIDTH, HEIGHT, FPS, BG_COLOR
from core.assets import Assets
from core.input import Input
from core.camera import Camera
from world.level import Level
from ui.hud import HUD


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        self.assets = Assets()
        self.assets.load()

        self.input = Input()
        self.camera = Camera()

        self.level = Level()
        self.hud = HUD(self.assets)

        # Jump signals
        self._jump_pressed = False
        self._jump_released = False
        self._jump_held = False

        # Dash signal (pressed this frame)
        self._dash_pressed = False

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            if dt > 0.05:
                dt = 0.05

            self._handle_events()
            self.input.update()

            self.level.update(
                dt,
                self.input,
                jump_pressed=self._jump_pressed,
                jump_released=self._jump_released,
                jump_held=self._jump_held,
                dash_pressed=self._dash_pressed,
            )

            # reset one-frame signals
            self._jump_pressed = False
            self._jump_released = False
            self._dash_pressed = False

            self.camera.update(self.level.player.rect)

            self.screen.fill(BG_COLOR)
            self.level.draw(self.screen, self.camera)
            self.hud.draw(self.screen, self.level)
            pygame.display.flip()

        pygame.quit()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

                if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    self._jump_pressed = True
                    self._jump_held = True

                if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self._dash_pressed = True

            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    self._jump_released = True
                    self._jump_held = False