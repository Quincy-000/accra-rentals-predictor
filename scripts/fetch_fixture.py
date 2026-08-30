"""Fetch a rendered MeQasa search page (live, local-only) into data/fixtures/.

Usage: ./venv/bin/python scripts/fetch_fixture.py --page 2
"""

import argparse
import re
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "data" / "fixtures"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
SEARCH_URL = "https://meqasa.com/apartments-for-rent-in-Accra"


def build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")  # required under WSL2
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1440,3000")
    opts.binary_location = "/usr/bin/google-chrome-stable"
    return webdriver.Chrome(options=opts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--page", type=int, default=2)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    driver = build_driver()
    try:
        driver.get(SEARCH_URL + f"?page={args.page}")
        # lazy-loaded cards need a beat + a scroll to materialise
        time.sleep(7)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        rows = driver.find_elements(By.CSS_SELECTOR, 'div[id^="feli"]')
        wrappers = driver.find_elements(By.CSS_SELECTOR, "div.mqs-prop-dt-wrapper")
        print(f"url: {driver.current_url}")
        print(f"feli rows: {len(rows)} | wrappers: {len(wrappers)}")
        if not rows:
            raise SystemExit("no feli rows found — page did not render; aborting")

        html = driver.page_source
        out = Path(args.out) if args.out else FIXTURE_DIR / f"search-page{args.page}.html"
        out.write_text(html, encoding="utf-8")
        RAW_DIR.mkdir(exist_ok=True)
        (RAW_DIR / f"search-page{args.page}-rendered.html").write_text(html, encoding="utf-8")
        print(f"saved: {out} ({len(html)/1024:.0f} KB)")

        # sanity: ids seen (non-clone)
        ids = sorted({re.match(r"feli(\d+)$", r.get_attribute("id")).group(1)
                      for r in rows if not r.get_attribute("id").endswith("_clone")
                      if re.match(r"feli\d+$", r.get_attribute("id"))})
        print(f"non-clone ids: {len(ids)} | sample: {ids[:8]} ... {ids[-4:]}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
