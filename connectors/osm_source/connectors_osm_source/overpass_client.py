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
TIMEOUT_S = 150.0

# (south, west, north, east) boxes covering Morocco *and* Western Sahara
# (Laâyoune, Dakhla, Smara, down to Lagouira) in full. Two boxes instead
# of one: a single box wide enough to reach Dakhla's -15.9W longitude
# also reaches north into the ~27.6-29.4N / -13.3..-18.2W band occupied
# by Spain's Canary Islands, which would get mislabelled as Moroccan
# data. Splitting at 27.5N (just above Laâyoune, below the southernmost
# Canary island) keeps the southern box tall/narrow enough for the
# Western Sahara coast without reaching the islands, and lets the
# northern box use a tighter western edge since mainland Morocco's coast
# never runs west of ~-13W above that latitude.
#
# An `area["ISO3166-1"="MA"]` lookup was considered instead of bboxes,
# but that relation's extent depends on how OSM tags the disputed
# southern provinces and can miss them; plain geographic boxes are
# unambiguous.
DEFAULT_BBOXES: tuple[tuple[float, float, float, float], ...] = (
    (20.6, -17.3, 27.5, -8.0),  # Western Sahara: Lagouira up to Laâyoune
    (27.5, -13.0, 36.0, -0.9),  # mainland Morocco: Tarfaya up to Tangier
)


def build_query(
    tag_key: str,
    tag_value: str,
    bboxes: tuple[tuple[float, float, float, float], ...] = DEFAULT_BBOXES,
) -> str:
    """Overpass QL: all nodes/ways/relations with `tag_key=tag_value`
    inside any of `bboxes` (each south, west, north, east), resolved to a
    single lat/lon via `out center` so ways and relations (not just
    nodes) yield a point."""
    statements = []
    for south, west, north, east in bboxes:
        bbox_str = f"{south},{west},{north},{east}"
        statements.append(f'  node["{tag_key}"="{tag_value}"]({bbox_str});')
        statements.append(f'  way["{tag_key}"="{tag_value}"]({bbox_str});')
        statements.append(f'  relation["{tag_key}"="{tag_value}"]({bbox_str});')
    body = "\n".join(statements)
    return f"""
[out:json][timeout:{int(TIMEOUT_S)}];
(
{body}
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
