# core/settings.py

TITLE = "Platformer (Python-only assets)"
WIDTH = 960
HEIGHT = 540
FPS = 60

# Physics
GRAVITY = 2600.0              # px/s^2
MAX_FALL_SPEED = 2400.0       # px/s
MOVE_SPEED = 380.0            # px/s
JUMP_SPEED = 820.0            # px/s

# Tilemap
TILE_SIZE = 48

# Colors (R,G,B)
BG_COLOR = (18, 18, 24)
TILE_COLOR = (70, 70, 88)
PLAYER_COLOR = (220, 220, 255)
HUD_COLOR = (245, 245, 255)

CAMERA_LERP = 0.18            # 0..1 higher = snappier camera

# --- Abilities ---
DASH_SPEED = 950.0            # px/s during dash
DASH_TIME = 0.14              # seconds dash lasts
DASH_COOLDOWN = 0.35          # seconds between dashes
AIR_DASHES = 1                # how many dashes allowed before landing (0=ground only)

WALL_SLIDE_SPEED = 320.0      # max fall speed while sliding
WALL_JUMP_X = 560.0           # horizontal push
WALL_JUMP_Y = 820.0           # vertical push (uses same feel as jump)
WALL_STICK_TIME = 0.10        # seconds to "stick" after contacting wall