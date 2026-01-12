# core/assets.py
# "Python-only assets": we generate fonts/colors/surfaces in code.

import pygame

class Assets:
    def __init__(self):
        self.font_small = None

    def load(self):
        # Default pygame font (no external file)
        self.font_small = pygame.font.Font(None, 22)