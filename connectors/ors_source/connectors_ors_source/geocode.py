"""Real-world geocoding via the public Nominatim API (OpenStreetMap),
used here to resolve commune names to real coordinates as isochrone
origins. Same endpoint and User-Agent convention already used by
`apps/api/platform_api/datasets.py` for the Portal's search box.
"""

from __future__ import annotations

import httpx

ENDPOINT = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "GeoSpacialData-POC/0.1 (support@geodata.local)"
TIMEOUT_S = 10.0


def geocode(query: str) -> tuple[float, float] | None:
    """Return (lon, lat) for the first Nominatim match, or None if the
    query has no result."""
    resp = httpx.get(
        ENDPOINT,
        params={"q": query, "format": "json", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_S,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        return None
    return float(results[0]["lon"]), float(results[0]["lat"])
