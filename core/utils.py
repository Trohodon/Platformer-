# core/utils.py

def clamp(value: float, lo: float, hi: float) -> float:
    return lo if value < lo else hi if value > hi else value