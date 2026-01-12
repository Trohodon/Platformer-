# Python 2D Platformer (Modular Project)

A simple 2D platformer written in Python, organized into multiple modules (`core/`, `world/`, `entities/`, `ui/`) so it scales cleanly as features grow (levels, enemies, menus, animations, etc.).

This repo is intentionally structured like a “real” project: `main.py` is the entry point, and the game systems live in focused packages.

---

## Project Structure

platformer/ main.py

core/ init.py game.py          # main loop, state switching, update/draw orchestration settings.py      # constants (resolution, FPS, gravity, colors) assets.py        # load/cache images, sounds, fonts input.py         # input mapping + helper functions camera.py        # camera follow + world-to-screen transforms utils.py         # small shared helpers

world/ init.py level.py         # level container: tiles + entities + spawn points tilemap.py       # tile grid, solids, collision helpers loader.py        # load levels from text/CSV/JSON (easy to swap later)

entities/ init.py player.py        # movement, gravity, jumping, collision enemy.py         # simple enemy AI (later) coin.py          # pickups / collectibles (later)

ui/ init.py hud.py           # HUD rendering (health, score, etc.) menu.py          # title/pause menu state (later)

assets/ images/          # sprites, tilesets, UI images sounds/          # SFX + music levels/          # level files (txt/csv/json)

> Notes:
> - Each folder is a Python package (has `__init__.py`) so imports stay clean.
> - `core/` is engine-like code (loop, settings, assets, input, camera).
> - `world/` manages levels and tile collision.
> - `entities/` holds game objects (player/enemies/pickups).
> - `ui/` is menus + HUD.
> - `assets/` is all external files.

---

## How It Works (High Level)

- `main.py` boots the game and hands control to `core/game.py`.
- `core/game.py` runs the main loop:
  - process input
  - update world + entities
  - render scene + UI
- `world/level.py` owns the current level:
  - tilemap
  - entity list
  - spawn points
- `entities/player.py` handles player physics:
  - velocity, gravity, jump
  - collision against solid tiles
- `core/camera.py` offsets the world so the player stays centered.

---

## Getting Started (Planned)

### 1) Create a virtual environment (recommended)
```bash
python -m venv .venv

Activate:

Windows

.venv\Scripts\activate

macOS/Linux

source .venv/bin/activate


2) Install dependencies

(We’ll use pygame-ce or pygame — whichever we choose in the next step.)

pip install -r requirements.txt

3) Run the game

python main.py


---

Roadmap

[ ] Base window + main loop

[ ] Player movement (left/right), gravity, jumping

[ ] Tilemap + solid collision

[ ] Camera follow + scrolling

[ ] Level loading from assets/levels/

[ ] HUD + pause menu

[ ] Basic enemy + collectible example

[ ] Optional: Tiled map editor support



---

License

Choose a license (MIT is common for game prototypes) and add it as LICENSE.

If you want, I can also add:
- a `requirements.txt`
- a `.gitignore` for Python + venv + build artifacts  
…and tailor the structure names to exactly what you want (ex: `gui/` instead of `ui/`).