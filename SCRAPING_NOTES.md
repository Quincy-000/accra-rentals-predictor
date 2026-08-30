# Scraper Spec — MeQasa (verified 2026-08-29/30, headless Chrome 152 + Selenium 4.48)

## URLs
- Search page: `https://meqasa.com/apartments-for-rent-in-Accra`
- Detail page (per card): `/apartment-for-rent-at-<Area>-<ID>?y=<track>`.
- Note: `/en/property-for-rent-in-accra` is a legacy shell → use the canonical path above.
- **`?page=N` does nothing.** The server ignores it (verified 2026-08-30: ?page=2/3,
  ?p=2, /page/2, ?offset=40 all return the same slice-1 content). Pagination is a
  client-side JS feature — see "Pagination" below.

## Page structure (read this before touching selectors)
Two `div.filtRpg` result batches: `#pg1` (30 wrappers) and `#pg2.unded` (16 wrappers) = 46
`div.mqs-prop-dt-wrapper` on page 1. **46 wrappers ≠ 46 listings.**

```
div#listview
└── div#pg1.filtRpg
    ├── div#plus-slider.flexslider          ← FEATURED CAROUSEL (FlexSlider)
    │   └── div.flex-viewport > ul.slides
    │       └── li | li.clone
    │           └── div#feli<ID>[_clone].row.mqs-featured-prop-inner-wrap
    │               ├── div.col-md-10 > div.mqs-prop-image-wrapper > div.mqs-prop-dt-wrapper   ← title/href/price, NO features
    │               └── div.col-md-10 > div.mqs-prop-dt-wrapper                                ← features <ul>, NO h2/href
    └── div#feli<ID>.row.mqs-featured-prop-inner-wrap        ← GRID CARD (32 of these across pg1+pg2)
        └── div.col-md-5 > div.mqs-prop-dt-wrapper           ← title/href/price AND features
└── div#pg2.filtRpg.unded  (same grid-card shape)
```

Page-1 arithmetic: 46 wrappers = 32 grid + 14 carousel halves (7 rows × 2) →
39 `feli` rows → 2 `_clone` rows dropped → **37 unique listings**.

## Card unit: the ROW, not the wrapper
```python
cards = [r for r in soup.select('div[id^="feli"]') if not r["id"].endswith("_clone")]
```
- The `feli<ID>` row is the common ancestor of **both** halves of a split carousel
  listing, so every field is reachable from one element — no filter, no merge.
- FlexSlider duplicates slides as `feli<ID>_clone` (page 1: `feli465037_clone`,
  `feli472452_clone`) — skip them.
- Listing ID comes from the row id: `re.match(r"feli(\d+)$", row["id"])`.

### Rejected alternatives (both lose data — do not reintroduce)
| approach | why it fails |
|---|---|
| `div.mqs-prop-dt-wrapper` filtered by `if c.select_one("h2 a")` | keeps 39 wrappers but the 7 carousel image-halves contain **zero `<li>`** → beds/baths/area become None on 5 real listings, and the 2 clones stay in as duplicate ids (39 rows, 37 unique). |
| `div.filtRpg div.mqs-prop-dt-wrapper` | the carousel is nested **inside** `#pg1.filtRpg`, so this returns all 46. `div.flexslider` is the discriminator, not `filtRpg`. |
| grid-only: `... :not(div.flexslider *)` | clean 32/32, but silently drops the 5 carousel-only listings per page. |

## Field selectors (relative to the `feli` row)
| Field | Selector / source | Notes |
|-------|-------------------|-------|
| id | row `id` attr → `feli(\d+)$` | canonical, unpadded |
| title | `h2 a` (text) | 37/37 |
| url | `h2 a[href]` | **href ID can be zero-padded** (`feli6680` ↔ `...-006680?y=…`) — never derive the id from it; strip the `?y=` tracking query |
| price | `p.h3` → `GH₵([\d,]+)` + `/\s*(day|week|month|year)` | text reads `Price GH₵2,300 / month`; 37/37 |
| beds | `li.bed span` | 37/37 (fallback: `(\d+)\s*bed` in title) |
| baths | `li.shower span` | 37/37 |
| garages | `li.garage span` | 28/37 — optional |
| area | `li.area span` | 16/37 — optional. **Unit is m², not sqft** (`100 m<sup>2</sup>`) |
| neighborhood | derived from title after `for rent in` | drop `Accra` / `Ghana` tokens |
| furnished | `"furnished" in title.lower()` | boolean feature |
| featured | `row.find_parent("div", class_="flexslider")` | 5 of 37 on page 1 |

## Pagination (how to actually page — discovered 2026-08-30)
- Clicking a page button (`onclick="mQpagejs('pg<N>',this)"`) fires
  `POST https://meqasa.com/filter2/selected` with form body
  `type=Apartment&contract=rent&beds=- Any -&baths=- Any -&loask=&hiask=&isfurnished=&region=- Any -&fsbo=&rentperiod=- Any -&localities=Accra&sort=date&slice=N&kw=&wye=<ts>`.
  The response HTML is inserted into the page; URL gains `?w=N` via pushState.
- Each slice renders: **32 constant core listings + ~16–20 new listings + a 5-slot
  featured carousel** (rotates from the pool). Verified across 12 fresh slices:
  35–52 rendered ids per slice, 32 of them identical every time; union of 12 slices
  = 194 unique. 222 slices (`data-limit=222` on the Next button) ≈ 3,5xx listings —
  consistent with the site's "3,533 available".
- The Next button's `pagenumnext` click is jQuery-bound and **unreliable from
  Selenium** (`element.click()` sometimes does nothing). Reliable approach: call
  `mQpagejs('pgN', element)` directly via `execute_script` for N = 2, 3, 4, …
- `mQpagejs` in a *fresh* session fetches slice N only (no accumulation across
  sessions); within one session the DOM **does** accumulate cards, so dedupe by id
  after every slice. Stop when a slice adds 0 new ids (first check: pg2 may add 0–3).
- Direct POST to `/filter2/selected` without a browser session returned HTML but
  0 cards (session/cookie-gated) — **do not rely on plain requests; use Selenium.**
- The `/resimp` POSTs fired on every page are favourite-icon tracking — ignore them.

## Data gotchas
1. **Price unit varies (`/ day`, `/ month`)** — page 1 has 5 daily listings. Normalize
   `month = day × 30`; keep `price_period` + `is_daily_rate` so they can be dropped
   later. ×30 pushes dailies to the top of the distribution (GH₵1,495/day → 44,850/mo)
   — decide at cleaning time whether to model or exclude them.
2. **Dedupe within a page as well as across pages.** The carousel repeats listings
   (page 1: 465037 and 472452 appear twice). Dedupe on the canonical `feli` id.
3. Neighborhood is dirty free text: `Cantonments` / `Cantoment` / `Cantoments`,
   `East Legon` / `Eastlegon` / `East legon 69`. Canonicalize during cleaning, not here.
4. Area outliers exist (one `5,000 m²` on a 3-bed) — validate before modelling.
5. Headless needs `--no-sandbox` in WSL2; page needs ~6s + one scroll for lazy cards.
6. `?page=N` stop condition: loop until a page yields 0 **new** ids. Still valid — but
   the carousel may repeat the same featured ids on every page, so measure new-id yield
   from grid + carousel combined and don't stop on the first low-yield page without
   checking. **Unverified: whether the carousel serves identical ids on page 2+**
   (only a page-1 fixture exists so far).

## Code layout
- `scraper/parser.py` — `parse_card(row)`, `parse_page(html)`, plus pure helpers
  (`parse_price`, `to_monthly`, `parse_area_m2`, `parse_neighborhood`).
- `tests/test_parser.py` — 46 fixture-based tests, no network. `./venv/bin/python -m pytest`
- Fixtures: `data/fixtures/search-page1.html` (raw copy in `data/raw/`).
- Live integration test stays local-only, never in GitHub Actions.

## Exploration scripts (repo root, throwaway)
`test_launch.py`, `explore_listing.py`, `explore_api.py`, `inspect_cards.py`,
`inspect_features.py`, `_verify_*.py`, `_smoke_parse.py` — not part of the package;
delete once the scraper is solid.
