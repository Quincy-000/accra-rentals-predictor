"""Multi-slice crawl loop for MeQasa search pages.

Pagination is client-side (see SCRAPING_NOTES.md): each page button fires
``mQpagejs('pgN')`` which POSTs to ``/filter2/selected?slice=N``. Every slice
renders the same 32 constant core listings plus ~16 new ones, and the DOM
*accumulates* cards across slices within one browser session.

This module is browser-agnostic: it takes a ``fetch_slice(n)`` callable that
returns the rendered page HTML for slice n (slice 1 = the initial page load).
``scripts/crawl_listings.py`` feeds it live Selenium output; the tests feed it
fixture HTML.

Stop condition: a single quiet slice is NORMAL (slice 2 often adds 0–3 ids), so
the loop only declares exhaustion after ``stop_after`` consecutive slices with
zero new ids. A hard cap (site's Next button shows data-limit=222) bounds the run.
"""

from __future__ import annotations

from typing import Callable

from .parser import parse_page

#: Hard cap from the site's own pagination (Next button data-limit).
MAX_SLICES = 222

#: Consecutive 0-new slices before declaring the pool exhausted.
STOP_AFTER = 2

FetchSlice = Callable[[int], str]
Progress = Callable[[dict], None]


def crawl_slices(
    fetch_slice: FetchSlice,
    max_slices: int = MAX_SLICES,
    stop_after: int = STOP_AFTER,
    progress: Progress | None = None,
) -> list[dict]:
    """Collect unique listings across slices until the pool is exhausted.

    ``fetch_slice(n)`` returns rendered HTML for slice n (1-based). Records are
    deduped by listing id; first occurrence wins (earlier slices take priority).
    Each call reports ``{"slice", "rendered", "new", "total"}`` to ``progress``.
    """
    seen: dict[str, dict] = {}
    quiet_runs = 0

    for n in range(1, max_slices + 1):
        records = parse_page(fetch_slice(n))
        new = [r for r in records if r["id"] not in seen]
        for record in new:
            seen[record["id"]] = record

        info = {"slice": n, "rendered": len(records), "new": len(new), "total": len(seen)}
        if progress:
            progress(info)

        if not new:
            quiet_runs += 1
            if quiet_runs >= stop_after:
                break
        else:
            quiet_runs = 0

    return list(seen.values())
