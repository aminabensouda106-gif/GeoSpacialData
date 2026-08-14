"""Thin client for the OpenRouteService (ORS) isochrones API.

Unlike Overpass/Nominatim, ORS requires a free API key
(https://openrouteservice.org/dev/#/signup). This module never embeds or
defaults a key — it reads `ORS_API_KEY` from the environment, the same
convention `connectors_base`'s S3 client uses for SeaweedFS credentials.
"""

from __future__ import annotations

import os

import httpx

DEFAULT_ENDPOINT = "https://api.openrouteservice.org/v2/isochrones/driving-car"
TIMEOUT_S = 30.0


class MissingApiKeyError(Exception):
    """Raised when ORS_API_KEY is not set in the environment."""


def isochrone(
    lon: float, lat: float, range_seconds: int, endpoint: str = DEFAULT_ENDPOINT
) -> dict:
    """Fetch a single driving-time isochrone polygon (GeoJSON
    FeatureCollection) around (lon, lat)."""
    api_key = os.environ.get("ORS_API_KEY")
    if not api_key:
        raise MissingApiKeyError(
            "ORS_API_KEY is not set. Get a free key at "
            "https://openrouteservice.org/dev/#/signup and export it as "
            "ORS_API_KEY before running this connector."
        )
    resp = httpx.post(
        endpoint,
        json={"locations": [[lon, lat]], "range": [range_seconds]},
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        timeout=TIMEOUT_S,
    )
    resp.raise_for_status()
    return resp.json()
