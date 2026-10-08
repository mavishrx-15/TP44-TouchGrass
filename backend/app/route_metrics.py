"""Geometric route measurements against the published tree dataset."""

from itertools import pairwise
from math import asin, cos, hypot, radians, sin, sqrt

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

EARTH_RADIUS_M = 6_371_000
ZONE_HALF_SIZE = 0.0005
TREE_CORRIDOR_M = 100


def dense_zone_share(path: list[tuple[float, float]], session: Session) -> float:
    """Return the route-distance fraction inside zones containing at least 10 trees."""
    segments = list(pairwise(path))
    total_length = sum(_distance_m(*start, *end) for start, end in segments)
    if not segments or total_length == 0:
        return 0.0

    latitudes = [point[0] for point in path]
    longitudes = [point[1] for point in path]
    rows = session.execute(
        text(
            """
            SELECT center_lat, center_lon FROM zones
            WHERE tree_count >= 10
              AND center_lat BETWEEN :south AND :north
              AND center_lon BETWEEN :west AND :east
            """
        ),
        {
            "south": min(latitudes) - ZONE_HALF_SIZE,
            "north": max(latitudes) + ZONE_HALF_SIZE,
            "west": min(longitudes) - ZONE_HALF_SIZE,
            "east": max(longitudes) + ZONE_HALF_SIZE,
        },
    ).all()
    rectangles = [
        (
            row.center_lon - ZONE_HALF_SIZE,
            row.center_lat - ZONE_HALF_SIZE,
            row.center_lon + ZONE_HALF_SIZE,
            row.center_lat + ZONE_HALF_SIZE,
        )
        for row in rows
    ]
    dense_length = 0.0
    for start, end in segments:
        segment_length = _distance_m(*start, *end)
        intervals = [
            interval
            for rectangle in rectangles
            if (interval := _clip_segment(start, end, rectangle)) is not None
        ]
        dense_length += segment_length * _union_length(intervals)
    return round(min(dense_length / total_length, 1.0), 3)


def high_pollen_tree_count(
    path: list[tuple[float, float]], species: list[str], session: Session
) -> int | None:
    """Count unique configured high-pollen trees within 100m of route segments.

    None means there is no configured species list; it must not be represented
    as a measured zero.
    """
    if not species:
        return None
    if not path:
        return 0

    max_lat = max(abs(point[0]) for point in path)
    lat_padding = TREE_CORRIDOR_M / 111_000
    lng_padding = TREE_CORRIDOR_M / (111_000 * max(cos(radians(max_lat)), 0.1))
    rows = session.execute(
        text(
            """
            SELECT com_id, latitude, longitude FROM trees
            WHERE lower(trim(common_name)) IN :species
              AND latitude BETWEEN :south AND :north
              AND longitude BETWEEN :west AND :east
            """
        ).bindparams(bindparam("species", expanding=True)),
        {
            "species": species,
            "south": min(point[0] for point in path) - lat_padding,
            "north": max(point[0] for point in path) + lat_padding,
            "west": min(point[1] for point in path) - lng_padding,
            "east": max(point[1] for point in path) + lng_padding,
        },
    ).all()
    return sum(
        1
        for row in rows
        if any(
            point_segment_distance_m(row.latitude, row.longitude, start, end) <= TREE_CORRIDOR_M
            for start, end in pairwise(path)
        )
        or (
            len(path) == 1 and _distance_m(row.latitude, row.longitude, *path[0]) <= TREE_CORRIDOR_M
        )
    )


def _clip_segment(
    start: tuple[float, float],
    end: tuple[float, float],
    rectangle: tuple[float, float, float, float],
) -> tuple[float, float] | None:
    """Liang-Barsky clipping in (longitude, latitude) coordinates."""
    lat1, lng1 = start
    lat2, lng2 = end
    west, south, east, north = rectangle
    dx, dy = lng2 - lng1, lat2 - lat1
    low, high = 0.0, 1.0
    for p, q in (
        (-dx, lng1 - west),
        (dx, east - lng1),
        (-dy, lat1 - south),
        (dy, north - lat1),
    ):
        if p == 0:
            if q < 0:
                return None
            continue
        ratio = q / p
        if p < 0:
            low = max(low, ratio)
        else:
            high = min(high, ratio)
        if low > high:
            return None
    return max(low, 0.0), min(high, 1.0)


def _union_length(intervals: list[tuple[float, float]]) -> float:
    if not intervals:
        return 0.0
    ordered = sorted(intervals)
    start, end = ordered[0]
    total = 0.0
    for next_start, next_end in ordered[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            total += end - start
            start, end = next_start, next_end
    return total + end - start


def point_segment_distance_m(
    lat: float, lng: float, start: tuple[float, float], end: tuple[float, float]
) -> float:
    reference_lat = radians((start[0] + end[0] + lat) / 3)
    x_scale = EARTH_RADIUS_M * cos(reference_lat) * radians(1)
    y_scale = EARTH_RADIUS_M * radians(1)
    start_x, start_y = start[1] * x_scale, start[0] * y_scale
    end_x, end_y = end[1] * x_scale, end[0] * y_scale
    point_x, point_y = lng * x_scale, lat * y_scale
    dx, dy = end_x - start_x, end_y - start_y
    denominator = dx * dx + dy * dy
    if denominator == 0:
        return hypot(point_x - start_x, point_y - start_y)
    fraction = max(
        0.0, min(1.0, ((point_x - start_x) * dx + (point_y - start_y) * dy) / denominator)
    )
    return hypot(point_x - (start_x + fraction * dx), point_y - (start_y + fraction * dy))


def _distance_m(lat_a: float, lng_a: float, lat_b: float, lng_b: float) -> float:
    delta_lat, delta_lng = radians(lat_b - lat_a), radians(lng_b - lng_a)
    value = (
        sin(delta_lat / 2) ** 2
        + cos(radians(lat_a)) * cos(radians(lat_b)) * sin(delta_lng / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * asin(sqrt(value))
