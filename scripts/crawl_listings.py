"""Crawl every MeQasa Accra rental listing into a JSON/CSV file.

Live, local-only — never run in CI. Drives the site's real pagination
(``mQpagejs('pgN')`` -> ``POST /filter2/selected``) from one browser session.

Usage:
    ./venv/bin/python scripts/crawl_listings.py                    # all slices -> data/listings.json
    ./venv/bin/python scripts/crawl_listings.py --max-slices 3 --csv --out /tmp/meqasa-smoke.json
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root on path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from scraper.crawl import MAX_SLICES, crawl_slices

SEARCH_URL = "https://meqasa.com/apartments-for-rent-in-Accra"


def build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")  # required under WSL2
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1440,3000")
    opts.binary_location = "/usr/bin/google-chrome-stable"
    return webdriver.Chrome(options=opts)


class SliceFetcher:
    """Fetch slice n of the search results from a live browser session.

    Slice 1 is the initial page load (needs a beat + a scroll for lazy cards).
    Slices 2+ call the page's own pagination handler ``mQpagejs('pgN')`` — the
    Next button is jQuery-bound and unreliable from Selenium, so we never click it.
    After the call we wait for the card count to grow past the pre-call baseline
    (or a timeout), then give the response a moment to finish rendering.
    """

    CARD_SELECTOR = 'div[id^="feli"]'

    def __init__(self, driver, grow_timeout: float = 12.0, settle: float = 1.5):
        self.driver = driver
        self.grow_timeout = grow_timeout
        self.settle = settle

    def __call__(self, n: int) -> str:
        if n == 1:
            self.driver.get(SEARCH_URL)
            time.sleep(7)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            return self.driver.page_source

        baseline = len(self.driver.find_elements(By.CSS_SELECTOR, self.CARD_SELECTOR))
        self.driver.execute_script(
            "var a=document.createElement('a');a.id='tmp-pg';document.body.appendChild(a);"
            f"mQpagejs('pg{n}',a);"
        )
        deadline = time.monotonic() + self.grow_timeout
        while time.monotonic() < deadline:
            time.sleep(0.5)
            count = len(self.driver.find_elements(By.CSS_SELECTOR, self.CARD_SELECTOR))
            if count > baseline:
                break
        time.sleep(self.settle)
        return self.driver.page_source


def save(records: list[dict], out_path: Path, with_csv: bool) -> None:
    out_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    if with_csv:
        csv_path = out_path.with_suffix(".csv")
        if records:
            with csv_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=list(records[0]))
                writer.writeheader()
                writer.writerows(records)
        else:
            csv_path.write_text("", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Crawl MeQasa Accra rentals (live, local-only).")
    ap.add_argument("--max-slices", type=int, default=MAX_SLICES,
                    help="hard cap on slices (site shows data-limit=222)")
    ap.add_argument("--out", type=str, default="data/listings.json")
    ap.add_argument("--csv", action="store_true", help="also write a CSV next to --out")
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    records: list[dict] = []
    driver = build_driver()
    try:
        fetcher = SliceFetcher(driver)

        def progress(info: dict) -> None:
            elapsed = time.monotonic() - started
            print(f"slice {info['slice']:3d}: rendered={info['rendered']:3d} "
                  f"new={info['new']:3d} total={info['total']:3d} ({elapsed:.0f}s)", flush=True)

        records = crawl_slices(fetcher, max_slices=args.max_slices, progress=progress)
    except KeyboardInterrupt:
        print("\ninterrupted — saving partial results")
    finally:
        driver.quit()

    elapsed = time.monotonic() - started
    save(records, out_path, args.csv)
    rate = len(records) / max(elapsed / 60, 1e-9)
    print(f"\nsaved {len(records)} unique listings to {out_path} "
          f"in {elapsed / 60:.1f} min ({rate:.0f} listings/min)")


if __name__ == "__main__":
    main()
