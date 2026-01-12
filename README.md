# Platformer-
platformer/
  main.py

  core/
    __init__.py
    game.py          # main loop, state switching
    settings.py      # constants (resolution, FPS, gravity)
    assets.py        # load/cache images/sounds
    input.py         # input mapping
    camera.py        # camera follow/scroll
    utils.py

  world/
    __init__.py
    level.py         # loads a level (tiles + entities)
    tilemap.py       # tile grid + collision solids
    loader.py        # load from JSON/CSV/Tiled exports

  entities/
    __init__.py
    player.py
    enemy.py
    coin.py

  ui/
    __init__.py
    hud.py
    menu.py

  assets/
    images/
    sounds/
    levels/