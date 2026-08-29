# Scraper Spec — MeQasa (verified 2026-08-29, headless Chrome 152 + Selenium 4.48)

## URLs
- Search page: `https://meqasa.com/apartments-for-rent-in-Accra`
- Pagination: append `?page=N` (N=1,2,3…). 3,533 listings total; ~39–46 cards per page.
- Detail page (per card): `/apartment-for-rent-at-<Area>-<ID>?y=<track>` — trailing `<ID>` is the unique listing id.
- Note: `/en/property-for-rent-in-accra` is a legacy shell → use the canonical path above.

## Card selectors (rendered DOM)
| Field | Selector | Notes |
|-------|----------|-------|
| Card | `div.mqs-prop-dt-wrapper` | one per listing |
| Title | `h2 a` (text) | e.g. "2 bedroom furnished apartment for rent in Accra, East Legon" |
| Detail link | `h2 a` (href) | extract id via regex `-(\d+)\?` |
| Price | `p.h3` | regex `GH₵([\d,]+) <span>/ (day|month)` |
| Bedrooms | `li.bed span` | text = count |
| Bathrooms | `li.shower span` | text = count |
| Area (sqft) | `li.area span` | present on ~40% of cards — optional field |

## Data gotchas
1. **Price unit varies: `/ day` and `/ month`** — saw `GH₵665 / day`. Normalize: `month = day * 30` (or flag/drop daily listings).
2. "furnished" appears in titles → derive boolean feature.
3. Neighborhood = parse from title suffix `"in Accra, <Neighborhood>"`.
4. Card count per page varies (39–46) — loop until a page yields 0 new ids, dedupe by id.
5. Headless needs `--no-sandbox` in WSL2; page needs ~6s + one scroll for lazy-loaded cards.

## Test fixture strategy (CI-safe)
- Save 1–2 rendered search pages as `data/fixtures/search-page1.html` (already saved from session; raw copy at `data/raw/`).
- pytest parses fixtures with the same card extractor → no live site in CI.
- Scraper integration test (live) is optional/local-only, never in GitHub Actions.

## Exploration scripts (kept in repo root, throwaway)
`test_launch.py`, `explore_listing.py`, `explore_api.py`, `inspect_cards.py`, `inspect_features.py` — not part of the package; delete when scraper is solid.
