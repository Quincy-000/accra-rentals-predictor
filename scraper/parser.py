"""MeQasa search-page parser.

Card unit is the listing ROW: ``div[id^="feli"]`` — NOT ``div.mqs-prop-dt-wrapper``.

Why: featured (carousel) listings are split across TWO wrappers — one holding
title/href/price, the other holding the bed/bath/area <ul>. The ``feli<ID>`` row is
the common ancestor of both halves, so every field is reachable from one element and
no merge/filter step is needed. The row id also carries the listing ID, which avoids
the zero-padded-href trap (``feli6680`` vs href ``...-006680?y=...``).

FlexSlider duplicates the carousel slides; those rows get a literal ``_clone`` suffix
(``feli465037_clone``) and are skipped here.

Verified against data/fixtures/search-page1.html (2026-08-29 capture):
46 wrappers -> 39 feli rows -> 2 clones skipped -> 37 unique listings,
title/price/beds/baths 37/37, garages 28/37, area 16/37.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

BASE_URL = "https://meqasa.com"

#: Every listing row on a search page (grid cards *and* featured carousel slides).
LISTING_ROW_SELECTOR = 'div[id^="feli"]'

_ROW_ID_RE = re.compile(r"^feli(\d+)$")
_AMOUNT_RE = re.compile(r"GH₵\s*([\d,]+(?:\.\d+)?)")
_PERIOD_RE = re.compile(r"/\s*(day|week|month|year)\b", re.I)
_AREA_RE = re.compile(r"([\d,]+(?:\.\d+)?)\s*m", re.I)
_TITLE_BEDS_RE = re.compile(r"(\d+)\s*bed", re.I)
_TITLE_SPLIT_RE = re.compile(r"\bfor rent in\b", re.I)
_INT_RE = re.compile(r"-?\d+")

#: Location tokens dropped from the neighborhood string (city / country noise).
_LOCATION_NOISE = {"accra", "ghana", "greater accra", "greater accra region"}

#: Multiplier used to express non-monthly prices as a monthly figure.
_PERIOD_TO_MONTH = {"month": 1.0, "day": 30.0, "week": 4.345, "year": 1 / 12}


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def _text(el, selector: str) -> str | None:
    """Text of the first match for ``selector``, or None. Collapses whitespace."""
    if el is None:
        return None
    found = el.select_one(selector)
    if found is None:
        return None
    text = found.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text) or None


def _to_int(value: str | None) -> int | None:
    if not value:
        return None
    match = _INT_RE.search(value.replace(",", ""))
    return int(match.group()) if match else None


def _to_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def _strip_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


# --------------------------------------------------------------------------- #
# field parsers (pure functions — unit-testable without HTML)
# --------------------------------------------------------------------------- #
def parse_price(price_text: str | None) -> tuple[int | None, str | None]:
    """``'Price GH₵2,300 / month'`` -> ``(2300, 'month')``.

    Returns ``(None, None)`` when the text is missing or unparseable, and
    ``(amount, None)`` when an amount is present but the period is not.
    """
    if not price_text:
        return None, None
    amount_match = _AMOUNT_RE.search(price_text)
    period_match = _PERIOD_RE.search(price_text)
    amount = _to_int(amount_match.group(1)) if amount_match else None
    period = period_match.group(1).lower() if period_match else None
    return amount, period


def to_monthly(amount: int | None, period: str | None) -> int | None:
    """Express ``amount`` as a monthly figure. Daily rents use ``x30`` (spec rule)."""
    if amount is None or period not in _PERIOD_TO_MONTH:
        return None
    return round(amount * _PERIOD_TO_MONTH[period])


def parse_area_m2(area_text: str | None) -> float | None:
    """``'100 m 2'`` / ``'5,000 m 2'`` -> ``100.0`` / ``5000.0``.

    Note: MeQasa renders ``100 m<sup>2</sup>`` — the unit is SQUARE METRES, not sqft.
    """
    if not area_text:
        return None
    match = _AREA_RE.search(area_text)
    return _to_float(match.group(1)) if match else None


def parse_neighborhood(title: str | None) -> str | None:
    """Pull the location tail out of a title and drop city/country noise.

    ``'... for rent in Accra, East Legon'``            -> ``'East Legon'``
    ``'... for rent in Afienya'``                      -> ``'Afienya'``
    ``'... in Airport Residential Area, Accra, Ghana'`` -> ``'Airport Residential Area'``
    """
    if not title:
        return None
    pieces = _TITLE_SPLIT_RE.split(title, maxsplit=1)
    if len(pieces) > 1:
        tail = pieces[1]
    elif " in " in title:
        tail = title.rsplit(" in ", 1)[1]
    else:
        return None
    parts = [p.strip() for p in tail.split(",")]
    kept = [p for p in parts if p and p.lower() not in _LOCATION_NOISE]
    if not kept:
        # title was e.g. "... for rent in Accra" — city is all we know
        return parts[0].strip() or None if parts else None
    return ", ".join(kept)


# --------------------------------------------------------------------------- #
# row-level parsing
# --------------------------------------------------------------------------- #
def is_clone_row(row) -> bool:
    """True for FlexSlider duplicate slides (``feli<ID>_clone``)."""
    return str(row.get("id", "")).endswith("_clone")


def row_listing_id(row) -> str | None:
    """Canonical listing id from the row id (``feli006680`` -> ``'6680'``)."""
    match = _ROW_ID_RE.match(str(row.get("id", "")))
    return str(int(match.group(1))) if match else None


def iter_listing_rows(soup):
    """Yield real listing rows: ``feli<digits>`` only, clones excluded."""
    for row in soup.select(LISTING_ROW_SELECTOR):
        if is_clone_row(row):
            continue
        if row_listing_id(row) is None:
            continue  # defensive: non-numeric feli* ids are not listings
        yield row


def parse_card(row) -> dict:
    """Parse one ``div#feli<ID>`` row into a flat record.

    Keys: id, url, href, title, price_ghs, price_period, price_ghs_month,
    is_daily_rate, beds, baths, garages, area_m2, neighborhood, furnished,
    is_featured.
    """
    listing_id = row_listing_id(row)
    link = row.select_one("h2 a")
    href = link.get("href") if link else None
    title = link.get_text(" ", strip=True) if link else None
    if title:
        title = re.sub(r"\s+", " ", title)

    price_amount, price_period = parse_price(_text(row, "p.h3"))
    beds = _to_int(_text(row, "li.bed span"))
    if beds is None and title:  # fallback: "2 bedroom apartment for rent ..."
        match = _TITLE_BEDS_RE.search(title)
        beds = int(match.group(1)) if match else None

    return {
        "id": listing_id,
        "url": urljoin(BASE_URL, _strip_query(href)) if href else None,
        "href": href,
        "title": title,
        "price_ghs": price_amount,
        "price_period": price_period,
        "price_ghs_month": to_monthly(price_amount, price_period),
        "is_daily_rate": price_period == "day",
        "beds": beds,
        "baths": _to_int(_text(row, "li.shower span")),
        "garages": _to_int(_text(row, "li.garage span")),
        "area_m2": parse_area_m2(_text(row, "li.area span")),
        "neighborhood": parse_neighborhood(title),
        "furnished": bool(title and "furnished" in title.lower()),
        "is_featured": row.find_parent("div", class_="flexslider") is not None,
    }


def parse_page(html: str, parser: str = "lxml") -> list[dict]:
    """Parse a rendered search page into unique listing records.

    Deduplicates by listing id *within* the page (the featured carousel repeats
    listings that also appear in the grid). First occurrence wins.
    """
    soup = BeautifulSoup(html, parser)
    records: dict[str, dict] = {}
    for row in iter_listing_rows(soup):
        record = parse_card(row)
        records.setdefault(record["id"], record)
    return list(records.values())
