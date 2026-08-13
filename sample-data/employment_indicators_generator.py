"""Synthetic generator for Dataset A (`employment_indicators`).

Stands in for a real statistics-office API so the `api_source` connector
runs end to end with zero credentials. Deterministic (seeded) so repeated
runs of the same period are reproducible, but each call still represents
"the API as it looks today" — a later run with a later `as_of` will emit
data for additional periods, which is what the connector's incremental
cursor is against.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from datetime import date

COMMUNES = [
    ("01-001", "Rabat"),
    ("01-002", "Salé"),
    ("01-003", "Témara"),
    ("02-001", "Casablanca"),
    ("02-002", "Mohammedia"),
    ("03-001", "Fès"),
    ("03-002", "Meknès"),
    ("04-001", "Marrakech"),
    ("05-001", "Tanger"),
    ("06-001", "Agadir"),
    ("07-001", "Laâyoune"),
]


def _months_between(start: date, end: date) -> Iterator[date]:
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        yield date(year, month, 1)
        month += 1
        if month > 12:
            month = 1
            year += 1


def generate_records(
    start_period: date = date(2024, 1, 1),
    as_of: date | None = None,
) -> Iterator[dict]:
    """Yield one synthetic record per (commune, month) between
    `start_period` and `as_of` inclusive. `as_of` defaults to today and
    plays the role of "the API's latest available period" — extract runs
    read up through here."""
    as_of = as_of or date.today()

    for commune_code, commune_name in COMMUNES:
        rng = random.Random(commune_code)  # stable per-commune series
        base_rate = rng.uniform(6.0, 14.0)
        for period in _months_between(start_period, as_of):
            drift = rng.uniform(-0.3, 0.3)
            base_rate = max(2.0, min(30.0, base_rate + drift))
            employment_count = rng.randint(5_000, 250_000)
            yield {
                "commune_code": commune_code,
                "commune_name": commune_name,
                "period": period.isoformat(),
                "employment_count": employment_count,
                "employment_rate": round(base_rate, 2),
            }
