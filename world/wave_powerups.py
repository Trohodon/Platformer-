# world/wave_powerups.py

# Wave number -> list of powerup IDs that should spawn at wave start
WAVE_POWERUPS = {
    1: ["speed"],
    2: ["hp_up"],
    3: ["damage"],
    4: ["dash_core"],
    5: ["armor", "frenzy"],

    # Example: later you can do multiple drops
    8: ["hp_up", "damage", "range"],
    10: ["wing"],
}