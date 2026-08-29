"""Exploration 2: capture MeQasa's XHR API + confirm cards render."""
import json, re, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-blink-features=AutomationControlled")
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
driver = webdriver.Chrome(options=options)

def api_urls(logs):
    out = set()
    for e in logs:
        try:
            msg = json.loads(e["message"])["message"]
            if msg.get("method") == "Network.responseReceived":
                u = msg["params"]["response"]["url"]
                if any(k in u.lower() for k in ("api", "search", "listing", "property", "rent", "elastic", "query")):
                    out.add(u)
        except Exception:
            pass
    return out

try:
    driver.get("https://meqasa.com/apartments-for-rent-in-Accra")
    time.sleep(8)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(4)
    print("TITLE:", driver.title)

    urls = api_urls(driver.get_log("performance"))
    print("\nAPI/INTERESTING URLS CAPTURED:")
    for u in sorted(urls):
        print("  ", u)

    # Card check: count elements that look like listing cards
    body_text = driver.find_element("tag name", "body").text
    print("\n'Bedroom' mentions in rendered text:", body_text.lower().count("bedroom"))
    print("'GH' price mentions:", body_text.count("GH"), "| 'per month':", body_text.lower().count("per month"))
    for line in [l.strip() for l in body_text.splitlines() if re.search(r"bedroom|GH₵|GHS|per month", l, re.I)][:12]:
        print("   |", line[:90])

    # Save full rendered HTML
    import pathlib
    out = pathlib.Path.home() / "accra-rentals-predictor" / "data" / "raw"
    (out / "search-accra-rendered.html").write_text(driver.page_source, encoding="utf-8")
    print("\nSaved rendered DOM -> data/raw/search-accra-rendered.html")
finally:
    driver.quit()
