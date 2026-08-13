"""Thin client for the public Overpass API.

Unlike `api_source`/`gee_source`, which pull from synthetic generators or
fixture scenes (MASTER_PROMPT M3's zero-credentials rule), Overpass needs
no API key or auth *and* is a genuine live source, so this connector
queries it directly: every run reflects whatever is mapped in
OpenStreetMap at query time, not a canned fixture.
"""

from __future__ import annotations

import httpx

DEFAULT_ENDPOINT = "https://overpass-api.de/api/interpreter"
TIMEOUT_S = 90.0

# (south, west, north, east) covering Morocco *and* Western Sahara (Laâyoune,
# Dakhla, Smara, down to Lagouira) in full. A bbox is used instead of an
# OSM `area["ISO3166-1"="MA"]` lookup because that relation's extent
# depends on how OSM tags the disputed southern provinces and can miss
# them; a plain geographic box is unambiguous and covers the whole area.
DEFAULT_BBOX = (20.7, -17.2, 36.0, -0.9)


def build_query(
    tag_key: str, tag_value: str, bbox: tuple[float, float, float, float] = DEFAULT_BBOX
) -> str:
    """Overpass QL: all nodes/ways/relations with `tag_key=tag_value`
    inside `bbox` (south, west, north, east), resolved to a single
    lat/lon via `out center` so ways and relations (not just nodes)
    yield a point."""
    south, west, north, east = bbox
    bbox_str = f"{south},{west},{north},{east}"
    return f"""
[out:json][timeout:{int(TIMEOUT_S)}];
(
  node["{tag_key}"="{tag_value}"]({bbox_str});
  way["{tag_key}"="{tag_value}"]({bbox_str});
  relation["{tag_key}"="{tag_value}"]({bbox_str});
);
out center tags;
""".strip()


USER_AGENT = "GeoSpacialData-POC/0.1 (support@geodata.local)"


def run_query(query: str, endpoint: str = DEFAULT_ENDPOINT) -> dict:
    """Execute an Overpass QL query against the live API and return the
    parsed JSON response (raises on a non-2xx status or a timeout). The
    public instance rejects requests with no identifying User-Agent."""
    resp = httpx.post(
        endpoint,
        data={"data": query},
        timeout=TIMEOUT_S,
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()
    return resp.json()
