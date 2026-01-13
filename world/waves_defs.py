# world/wave_defs.py
"""
Wave definitions live here so you can edit without touching Level code.

Each wave is a dict:
{
  "name": "Wave 1",
  "entries": [
      {"type": "basic", "count": 8},
      {"type": "basic", "count": 4},
  ]
}

Later you can add new enemy types:
  {"type": "jumper", "count": 3}
  {"type": "tank", "count": 1}
"""

WAVES = [
    {
        "name": "Wave 1",
        "entries": [
            {"type": "basic", "count": 10},
        ],
    },
    {
        "name": "Wave 2",
        "entries": [
            {"type": "basic", "count": 14},
        ],
    },
    {
        "name": "Wave 3",
        "entries": [
            {"type": "basic", "count": 18},
        ],
    },
]