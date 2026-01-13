# world/waves.py
from typing import Dict, List, Optional


class WaveManager:
    """
    Dedicated wave system.
    - Waves are defined as a list of "entries"
    - Each entry describes what enemy type and how many to spawn
    - Level asks WaveManager when to spawn, and WaveManager decides when the next wave starts
    """

    def __init__(self, wave_defs: List[Dict], cooldown: float = 1.2):
        self.wave_defs = wave_defs
        self.cooldown = float(cooldown)

        self.wave_index = 0          # 0-based internally
        self.active = False
        self.timer = 0.6             # small initial delay so game isn't instant chaos

    @property
    def wave_number(self) -> int:
        return self.wave_index + 1

    def is_finished(self) -> bool:
        return self.wave_index >= len(self.wave_defs)

    def current_wave_def(self) -> Optional[Dict]:
        if self.is_finished():
            return None
        return self.wave_defs[self.wave_index]

    def update(self, dt: float, alive_enemy_count: int) -> bool:
        """
        Returns True if a new wave should start NOW (Level should spawn it).
        """
        if self.is_finished():
            return False

        if not self.active:
            self.timer -= dt
            if self.timer <= 0.0:
                self.active = True
                return True
            return False

        # active wave: wait until all enemies are dead
        if alive_enemy_count <= 0:
            self.active = False
            self.timer = self.cooldown
            self.wave_index += 1
            return False

        return False

    def mark_wave_started(self):
        self.active = True