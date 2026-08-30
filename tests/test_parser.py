"""Fixture-first parser tests — never touches the live site (CI-safe).

Fixture: data/fixtures/search-page1.html (rendered search page, 2026-08-29).
Ground truth verified by hand that session:
  46 div.mqs-prop-dt-wrapper  ->  39 div[id^=feli] rows  ->  2 clones  ->  37 listings
"""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from scraper.parser import (
    iter_listing_rows,
    parse_area_m2,
    parse_card,
    parse_neighborhood,
    parse_page,
    parse_price,
    to_monthly,
)

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "search-page1.html"


@pytest.fixture(scope="module")
def html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def soup(html) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


@pytest.fixture(scope="module")
def records(html) -> list[dict]:
    return parse_page(html)


@pytest.fixture(scope="module")
def by_id(records) -> dict[str, dict]:
    return {r["id"]: r for r in records}


# --------------------------------------------------------------------------- #
# structure: the split-card / clone trap
# --------------------------------------------------------------------------- #
def test_wrapper_count_is_the_trap_we_avoid(soup):
    """46 wrappers != 46 listings — this is why the row is the card unit."""
    assert len(soup.select("div.mqs-prop-dt-wrapper")) == 46


def test_row_selector_finds_39_rows_including_clones(soup):
    assert len(soup.select('div[id^="feli"]')) == 39


def test_clone_rows_are_skipped(soup):
    clones = [r for r in soup.select('div[id^="feli"]') if str(r.get("id")).endswith("_clone")]
    assert {r["id"] for r in clones} == {"feli465037_clone", "feli472452_clone"}
    assert len(list(iter_listing_rows(soup))) == 37


def test_page_yields_37_unique_listings(records):
    assert len(records) == 37
    ids = [r["id"] for r in records]
    assert len(set(ids)) == 37


def test_cloned_listings_survive_exactly_once(by_id):
    for listing_id in ("465037", "472452"):
        assert listing_id in by_id


def test_five_listings_come_from_the_featured_carousel(records):
    featured = [r["id"] for r in records if r["is_featured"]]
    assert sorted(featured) == sorted(["472452", "472400", "472704", "263030", "465037"])


# --------------------------------------------------------------------------- #
# field coverage: the regression that the h2-filter approach caused
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("field", ["id", "title", "price_ghs", "price_period", "beds", "baths", "url"])
def test_core_fields_complete_on_every_listing(records, field):
    missing = [r["id"] for r in records if r[field] in (None, "")]
    assert missing == [], f"{field} missing on {missing}"


def test_optional_field_coverage_matches_fixture(records):
    assert sum(1 for r in records if r["area_m2"] is not None) == 16
    assert sum(1 for r in records if r["garages"] is not None) == 28


def test_featured_listings_keep_their_bed_bath_data(by_id):
    """These are the 5 that lost beds/baths under the discard-fragments fix."""
    expected = {
        "465037": (1, 1),
        "472452": (2, 2),
        "472400": (2, 3),
        "472704": (1, 1),
        "263030": (1, 1),
    }
    actual = {k: (by_id[k]["beds"], by_id[k]["baths"]) for k in expected}
    assert actual == expected


# --------------------------------------------------------------------------- #
# ids and urls
# --------------------------------------------------------------------------- #
def test_ids_are_canonical_unpadded_digits(records):
    assert all(r["id"].isdigit() and not r["id"].startswith("0") for r in records)


def test_zero_padded_href_does_not_corrupt_the_id(by_id):
    """feli6680 has href ...-006680?y=... — the row id is the trustworthy source."""
    record = by_id["6680"]
    assert "006680" in record["href"]
    assert record["id"] == "6680"


def test_url_is_absolute_and_query_stripped(by_id):
    url = by_id["6680"]["url"]
    assert url.startswith("https://meqasa.com/")
    assert "?" not in url


# --------------------------------------------------------------------------- #
# value parsing
# --------------------------------------------------------------------------- #
def test_monthly_listing_parsed(by_id):
    record = by_id["472452"]
    assert (record["price_ghs"], record["price_period"]) == (2300, "month")
    assert record["price_ghs_month"] == 2300
    assert record["is_daily_rate"] is False


def test_daily_listing_normalised_to_month(by_id):
    record = by_id["465037"]
    assert (record["price_ghs"], record["price_period"]) == (665, "day")
    assert record["price_ghs_month"] == 665 * 30
    assert record["is_daily_rate"] is True


def test_neighborhood_and_furnished_flags(by_id):
    assert by_id["263030"]["neighborhood"] == "Spintex"
    assert by_id["263030"]["furnished"] is True
    assert by_id["472452"]["neighborhood"] == "Afienya"
    assert by_id["472452"]["furnished"] is False
    assert by_id["6680"]["neighborhood"] == "Airport Residential Area"


def test_area_is_square_metres(by_id):
    assert by_id["263030"]["area_m2"] == 100.0


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Price GH₵2,300 / month", (2300, "month")),
        ("Price GH₵665 / day", (665, "day")),
        ("Price GH₵44,562 / month", (44562, "month")),
        ("GH₵1,200", (1200, None)),
        (None, (None, None)),
        ("negotiable", (None, None)),
    ],
)
def test_parse_price_cases(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize(
    "amount,period,expected",
    [(2300, "month", 2300), (665, "day", 19950), (1000, "week", 4345), (None, "month", None), (500, None, None)],
)
def test_to_monthly_cases(amount, period, expected):
    assert to_monthly(amount, period) == expected


@pytest.mark.parametrize(
    "text,expected",
    [("100 m 2", 100.0), ("5,000 m 2", 5000.0), ("47 m 2", 47.0), (None, None), ("--", None)],
)
def test_parse_area_cases(text, expected):
    assert parse_area_m2(text) == expected


@pytest.mark.parametrize(
    "title,expected",
    [
        ("1 bedroom furnished apartment for rent in Accra, East Legon", "East Legon"),
        ("2 bedroom apartment for rent in Afienya", "Afienya"),
        ("3 bedroom furnished apartment for rent in Airport Residential Area, Accra, Ghana", "Airport Residential Area"),
        ("1 bedroom furnished apartment for rent in Accra, OSU, RINGWAY ESTATE", "OSU, RINGWAY ESTATE"),
        ("2 bedroom furnished apartment for rent in West Hills Mall", "West Hills Mall"),
        ("studio apartment for rent in Accra", "Accra"),
        (None, None),
    ],
)
def test_parse_neighborhood_cases(title, expected):
    assert parse_neighborhood(title) == expected


# --------------------------------------------------------------------------- #
# parse_card contract
# --------------------------------------------------------------------------- #
def test_parse_card_returns_stable_schema(soup):
    row = next(iter_listing_rows(soup))
    record = parse_card(row)
    assert set(record) == {
        "id", "url", "href", "title", "price_ghs", "price_period", "price_ghs_month",
        "is_daily_rate", "beds", "baths", "garages", "area_m2", "neighborhood",
        "furnished", "is_featured",
    }
