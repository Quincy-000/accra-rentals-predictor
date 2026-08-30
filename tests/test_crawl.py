"""Crawl-loop tests: dedupe, exhaustion guard, cap. Fixture-fed, no network.

Fixtures slice-N.html are SINGLE-SLICE captures (fresh session per slice, no DOM
accumulation): slice-1 = 35 ids, slice-2 = 35, slice-3 = 50, slice-12 = 52.
search-pageN.html (also in fixtures/) are cumulative click-session captures — the
crawl tests must not use those.
"""

from pathlib import Path

import pytest

from scraper.crawl import crawl_slices
from scraper.parser import parse_page

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def ids(records: list[dict]) -> set[str]:
    return {r["id"] for r in records}


def make_fetcher(sequence: list[str]):
    """fetch_slice(n) returning the n-th fixture in ``sequence`` (1-based)."""
    calls: list[int] = []

    def fetch(n: int) -> str:
        calls.append(n)
        return load(sequence[n - 1])

    return fetch, calls


# --------------------------------------------------------------------------- #
# dedupe + union
# --------------------------------------------------------------------------- #
def test_crawl_dedupes_across_slices():
    seq = ["slice-1.html", "slice-2.html", "slice-3.html", "slice-12.html"]
    fetch, _ = make_fetcher(seq)
    records = crawl_slices(fetch, max_slices=len(seq), stop_after=1)

    expected = set().union(*(ids(parse_page(load(f))) for f in seq))
    assert ids(records) == expected
    assert len(records) == len(expected)  # no duplicates


def test_first_occurrence_wins():
    seq = ["slice-2.html", "slice-1.html"]  # reversed order vs natural
    fetch, _ = make_fetcher(seq)
    records = crawl_slices(fetch, max_slices=2, stop_after=1)

    expected = ids(parse_page(load("slice-2.html"))) | ids(parse_page(load("slice-1.html")))
    assert ids(records) == expected


# --------------------------------------------------------------------------- #
# stop conditions
# --------------------------------------------------------------------------- #
def test_single_quiet_slice_does_not_stop():
    """slice 2 often adds 0-3 ids; one quiet slice must not end the crawl."""
    seq = ["slice-1.html", "slice-2.html", "slice-3.html"]
    fetch, calls = make_fetcher(seq)
    records = crawl_slices(fetch, max_slices=3, stop_after=2)
    assert calls == [1, 2, 3]  # kept going past the quiet slice 2


def test_stops_after_two_consecutive_empty_slices():
    seq = ["slice-1.html", "slice-2.html", "slice-3.html", "slice-12.html", "slice-12.html", "slice-12.html"]
    fetch, calls = make_fetcher(seq)
    records = crawl_slices(fetch, max_slices=len(seq), stop_after=2)
    assert calls == [1, 2, 3, 4, 5, 6]  # slices 5 & 6 both added nothing -> stop
    assert len(ids(records)) == len(
        ids(parse_page(load("slice-1.html")))
        | ids(parse_page(load("slice-2.html")))
        | ids(parse_page(load("slice-3.html")))
        | ids(parse_page(load("slice-12.html")))
    )


def test_respects_max_slices():
    seq = ["slice-1.html", "slice-2.html", "slice-3.html", "slice-12.html"]
    fetch, calls = make_fetcher(seq)
    records = crawl_slices(fetch, max_slices=2, stop_after=1)
    assert calls == [1, 2]
    expected = ids(parse_page(load("slice-1.html"))) | ids(parse_page(load("slice-2.html")))
    assert ids(records) == expected


# --------------------------------------------------------------------------- #
# progress reporting
# --------------------------------------------------------------------------- #
def test_progress_reports_monotonic_totals():
    seq = ["slice-1.html", "slice-2.html", "slice-3.html"]
    fetch, _ = make_fetcher(seq)
    infos: list[dict] = []
    records = crawl_slices(fetch, max_slices=3, stop_after=2, progress=infos.append)

    assert len(infos) == 3
    totals = [i["total"] for i in infos]
    assert totals == sorted(totals)  # non-decreasing
    assert infos[0]["new"] == infos[0]["rendered"]
    assert totals[-1] == len(records)
    for info in infos:
        assert info["slice"] >= 1 and info["new"] >= 0
