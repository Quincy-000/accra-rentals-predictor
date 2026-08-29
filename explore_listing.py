"""Exploration: find MeQasa listing-page selectors for price/beds/baths/location."""
import re, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-blink-features=AutomationControlled")
driver = webdriver.Chrome(options=options)

try:
    # 1. Search page: collect listing links
    driver.get("https://www.meqasa.com/en/property-for-rent-in-accra")
    time.sleep(6)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)
    anchors = driver.find_elements("css selector", "a[href]")
    hrefs = []
    for a in anchors:
        h = a.get_attribute("href") or ""
        if "/property-for-rent" in h and h not in hrefs:
            hrefs.append(h)
    print("LISTING LINKS FOUND:", len(hrefs))
    for h in hrefs[:5]:
        print(" ", h)

    if not hrefs:
        print("NO LISTING LINKS — dumping page title:", driver.title)
        raise SystemExit(1)

    # 2. Open the first listing page
    driver.get(hrefs[0])
    time.sleep(6)
    print("\nLISTING TITLE:", driver.title)
    print("LISTING URL:", driver.current_url)

    # 3. Find price text anywhere (GH / cedis / per month patterns)
    body_text = driver.find_element("tag name", "body").text
    price_lines = [l.strip() for l in body_text.splitlines()
                   if re.search(r"(GH|GH₵|GHS|₵|\bGhana cedis?|per month|monthly)", l, re.I) and len(l.strip()) < 60]
    print("\nPRICE-LIKE LINES (first 15):")
    for l in price_lines[:15]:
        print("  |", l)

    # 4. Bedrooms / bathrooms / location lines
    feat_lines = [l.strip() for l in body_text.splitlines()
                  if re.search(r"(bedroom|bathroom|toilet|location|area|region|furnish)", l, re.I) and len(l.strip()) < 80]
    print("\nFEATURE-LIKE LINES (first 20):")
    for l in feat_lines[:20]:
        print("  |", l)

    # 5. Look for structured JSON in page source (price often in embedded data)
    src = driver.page_source
    m = re.findall(r'"(?:price|priceValue|rent|monthlyRent|amount)"\s*:\s*"?[0-9,\.]+', src)
    print("\nJSON PRICE KEYS IN SOURCE:", len(m))
    for x in m[:10]:
        print("  ", x)

    # 6. Save raw HTML for later fixture use
    import pathlib
    out = pathlib.Path.home() / "accra-rentals-predictor" / "data" / "raw"
    out.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", hrefs[0])[:80]
    (out / f"listing-{safe}.html").write_text(src, encoding="utf-8")
    print("\nSaved raw HTML ->", out / f"listing-{safe}.html")
finally:
    driver.quit()
