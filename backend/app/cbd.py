"""Melbourne CBD boundary shared by Sprout's map, search restriction and
weather lookup (Epic 5, US5.5).

The "Melbourne" precinct in `zones`/`trees` (456 zones) turned out to cover
far more than the CBD a user would recognise - it reaches into Yarra Park,
Jolimont and the Botanic Gardens fringe. This box is trimmed to the Hoddle
Grid itself (Spencer-Spring St, Flinders-La Trobe St, plus a small margin),
which keeps 226 real zones - still precinct='Melbourne' data, just the
colloquial "CBD" subset of it rather than the full municipal boundary.
"""

CBD_BOUNDS = {
    "south": -37.8230,
    "north": -37.8048,
    "west": 144.9528,
    "east": 144.9722,
}

CBD_CENTER = {
    "lat": (CBD_BOUNDS["south"] + CBD_BOUNDS["north"]) / 2,
    "lng": (CBD_BOUNDS["west"] + CBD_BOUNDS["east"]) / 2,
}

# The precinct name in `trees`/`zones` that corresponds to this box.
CBD_PRECINCT_NAME = "Melbourne"
