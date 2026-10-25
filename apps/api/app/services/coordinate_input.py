"""Explicit coordinate parsing; projected conversion uses the existing PostGIS runtime."""

import math
import re
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select


class CoordinateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source_crs: Literal["EPSG:4326", "EPSG:32648"]
    axis_order: Literal["longitude_latitude", "latitude_longitude", "easting_northing"]
    format: Literal["decimal", "dms", "utm"]
    x: str
    y: str


def _decimal(value: str) -> tuple[float, int]:
    if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value.strip()):
        raise ValueError("Decimal coordinates require unambiguous dot-decimal strings")
    try:
        parsed = Decimal(value.strip())
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal coordinate") from exc
    if not parsed.is_finite():
        raise ValueError("Coordinate must be finite")
    return float(parsed), max(0, -parsed.as_tuple().exponent)


def _dms(value: str, axis: str) -> tuple[float, int]:
    # Accept conventional DMS symbols or an explicitly space-separated triple.
    match = re.fullmatch(
        r"\s*([+-]?\d+(?:\.\d+)?)\s*(?:[°ºd]\s*|\s+)"
        r"(\d+(?:\.\d+)?)\s*(?:['′m]\s*|\s+)"
        r"(\d+(?:\.\d+)?)\s*(?:[\"″]\s*)?([NSEW])?\s*",
        value,
        re.IGNORECASE,
    )
    if not match:
        raise ValueError(
            "DMS requires degrees, minutes, seconds and consistent hemisphere"
        )
    degrees, minutes, seconds = (float(match[i]) for i in (1, 2, 3))
    hemisphere = (match[4] or "").upper()
    if minutes >= 60 or seconds >= 60:
        raise ValueError("DMS minutes and seconds must be below 60")
    if hemisphere and hemisphere not in ("EW" if axis == "longitude" else "NS"):
        raise ValueError("Hemisphere contradicts declared axis order")
    if hemisphere and match[1].startswith("-"):
        raise ValueError("Use hemisphere or signed degrees, not both")
    sign = -1 if match[1].startswith("-") or hemisphere in ("W", "S") else 1
    decimal = sign * (abs(degrees) + minutes / 60 + seconds / 3600)
    limit = 180 if axis == "longitude" else 90
    if abs(decimal) > limit:
        raise ValueError("DMS exceeds axis range")
    seconds_precision = _decimal(match[3])[1]
    return decimal, seconds_precision


def parse_coordinates(value: CoordinateInput, db=None) -> dict:
    """Return lon/lat with original strings and declared precision; never infer CRS."""
    if value.source_crs == "EPSG:32648":
        if value.axis_order != "easting_northing" or value.format != "utm":
            raise ValueError("EPSG:32648 requires explicit UTM easting/northing metres")
        easting, px = _decimal(value.x)
        northing, py = _decimal(value.y)
        if not 166_000 <= easting <= 834_000 or not 0 <= northing <= 9_330_000:
            raise ValueError(
                "Coordinates outside UTM48N bounds; check CRS and axis order"
            )
        if db is None:
            raise ValueError("UTM conversion requires the existing PostGIS database")
        point = func.ST_Transform(
            func.ST_SetSRID(func.ST_Point(easting, northing), 32648), 4326
        )
        row = db.execute(select(func.ST_X(point), func.ST_Y(point))).one()
        longitude, latitude = float(row[0]), float(row[1])
        if not 102 <= longitude <= 108 or not 0 <= latitude <= 84:
            raise ValueError("Converted position lies outside EPSG:32648 area of use")
        method = "PostGIS ST_Transform EPSG:32648 to EPSG:4326; easting/northing metres"
        precision_unit = "metres"
    else:
        if value.axis_order == "easting_northing" or value.format == "utm":
            raise ValueError(
                "EPSG:4326 requires explicit longitude/latitude degree axes"
            )
        axes = (
            ("longitude", "latitude")
            if value.axis_order == "longitude_latitude"
            else ("latitude", "longitude")
        )
        parser = (lambda v, axis: _decimal(v)) if value.format == "decimal" else _dms
        x, px = parser(value.x, axes[0])
        y, py = parser(value.y, axes[1])
        longitude, latitude = (x, y) if axes[0] == "longitude" else (y, x)
        method = (
            "Declared WGS84 decimal degrees"
            if value.format == "decimal"
            else "DMS degrees + minutes/60 + seconds/3600; declared WGS84"
        )
        precision_unit = (
            "decimal degrees" if value.format == "decimal" else "arcseconds"
        )
    if (
        not all(math.isfinite(v) for v in (longitude, latitude))
        or not -180 <= longitude <= 180
        or not -90 <= latitude <= 90
    ):
        raise ValueError(
            "Position outside finite longitude/latitude range; check axis order"
        )
    return {
        "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
        "original": value.model_dump(),
        "method": method,
        "input_decimal_places": [px, py],
        "input_precision_unit": precision_unit,
        "precision_note": "Reported digit precision is not positional accuracy; output is not surveyed geometry.",
    }


def distance_metres(a, b):
    """Screening distance, not an accuracy estimate or geometry validation."""
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 6_371_008.8 * 2 * math.asin(min(1, math.sqrt(h)))
