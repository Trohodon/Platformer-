# core/abilities.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def diminishing_returns(stacks: int, per_stack: float, cap: float) -> float:
    """
    Smooth diminishing returns:
    value = cap * (1 - (1 - per_stack/cap)^stacks)
    """
    if stacks <= 0:
        return 0.0
    per_stack = max(0.0, per_stack)
    cap = max(0.00001, cap)
    base = 1.0 - (per_stack / cap)
    base = clamp(base, 0.0, 1.0)
    return cap * (1.0 - (base ** stacks))


@dataclass
class AbilityBase:
    # Movement
    run_speed: float = 230.0
    air_control: float = 1.0
    jump_speed: float = 820.0
    max_jumps: int = 2

    dash_speed: float = 560.0
    dash_time: float = 0.14
    dash_cooldown: float = 0.55
    air_dashes_max: int = 1

    # Combat
    bullet_damage: int = 20
    bullet_speed: float = 820.0
    fire_rate: float = 0.18  # seconds between shots

    # Survivability
    max_health: int = 100
    spike_damage: int = 30
    damage_taken_mult: float = 1.0   # lower is better
    regen_per_sec: float = 0.0
    i_frames: float = 0.18


@dataclass
class Abilities:
    """
    Powerup stacks -> derived stats.
    Read these properties everywhere instead of hardcoding.
    """
    base: AbilityBase = field(default_factory=AbilityBase)
    stacks: Dict[str, int] = field(default_factory=dict)

    def get_stack(self, powerup_id: str) -> int:
        return int(self.stacks.get(powerup_id, 0))

    def add_stack(self, powerup_id: str, amount: int = 1) -> int:
        self.stacks[powerup_id] = self.get_stack(powerup_id) + int(amount)
        return self.stacks[powerup_id]

    # -------------------------
    # Derived Stats
    # -------------------------
    @property
    def max_health(self) -> int:
        bonus = diminishing_returns(self.get_stack("hp_up"), per_stack=20.0, cap=140.0)
        return int(self.base.max_health + bonus)

    @property
    def run_speed(self) -> float:
        bonus = diminishing_returns(self.get_stack("speed"), per_stack=35.0, cap=220.0)
        bonus += diminishing_returns(self.get_stack("agility"), per_stack=18.0, cap=120.0)
        return self.base.run_speed + bonus

    @property
    def air_control(self) -> float:
        bonus = diminishing_returns(self.get_stack("agility"), per_stack=0.10, cap=0.50)
        return self.base.air_control + bonus

    @property
    def jump_speed(self) -> float:
        bonus = diminishing_returns(self.get_stack("jump"), per_stack=40.0, cap=200.0)
        return self.base.jump_speed + bonus

    @property
    def max_jumps(self) -> int:
        s = self.get_stack("wing")
        extra = 0
        if s >= 2:
            extra = 1
        if s >= 5:
            extra = 2
        return self.base.max_jumps + extra

    @property
    def dash_cooldown(self) -> float:
        s = self.get_stack("dash_core")
        reduction = diminishing_returns(s, per_stack=0.07, cap=0.30)
        return max(0.18, self.base.dash_cooldown - reduction)

    @property
    def dash_speed(self) -> float:
        bonus = diminishing_returns(self.get_stack("dash_core"), per_stack=35.0, cap=160.0)
        return self.base.dash_speed + bonus

    @property
    def dash_time(self) -> float:
        bonus = diminishing_returns(self.get_stack("dash_core"), per_stack=0.01, cap=0.04)
        return self.base.dash_time + bonus

    @property
    def air_dashes_max(self) -> int:
        return self.base.air_dashes_max + (1 if self.get_stack("dash_core") >= 4 else 0)

    @property
    def bullet_damage(self) -> int:
        bonus = diminishing_returns(self.get_stack("damage"), per_stack=6.0, cap=45.0)
        bonus += diminishing_returns(self.get_stack("frenzy"), per_stack=3.0, cap=20.0)
        return int(self.base.bullet_damage + bonus)

    @property
    def bullet_speed(self) -> float:
        bonus = diminishing_returns(self.get_stack("range"), per_stack=90.0, cap=420.0)
        return self.base.bullet_speed + bonus

    @property
    def fire_rate(self) -> float:
        s = self.get_stack("frenzy")
        reduction = diminishing_returns(s, per_stack=0.020, cap=0.090)
        return max(0.07, self.base.fire_rate - reduction)

    @property
    def damage_taken_mult(self) -> float:
        s = self.get_stack("armor")
        reduction = diminishing_returns(s, per_stack=0.06, cap=0.45)
        return max(0.55, self.base.damage_taken_mult - reduction)

    @property
    def regen_per_sec(self) -> float:
        return diminishing_returns(self.get_stack("regen"), per_stack=1.5, cap=6.0)

    @property
    def spike_damage(self) -> int:
        s = self.get_stack("spike_resist")
        reduction = diminishing_returns(s, per_stack=5.0, cap=22.0)
        return max(8, int(self.base.spike_damage - reduction))

    @property
    def i_frames(self) -> float:
        bonus = diminishing_returns(self.get_stack("tenacity"), per_stack=0.05, cap=0.20)
        return self.base.i_frames + bonus