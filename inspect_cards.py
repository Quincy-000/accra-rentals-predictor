"""Extract card structure from saved rendered DOM: class names + link patterns."""
import re, pathlib

html = (pathlib.Path.home() / "accra-rentals-predictor" / "data" / "raw" / "search-accra-rendered.html").read_text(encoding="utf-8")
print("FILE SIZE:", len(html))

# 1. Listing detail links
links = sorted(set(re.findall(r'href="([^"]*for-rent[^"]*)"', html)))
print("\nDETAIL LINK PATTERNS (%d):" % len(links))
for l in links[:10]:
    print("  ", l)

# 2. HTML context around a price (GH₵) to see the card classes
print("\n--- CONTEXT AROUND FIRST 3 PRICES ---")
for m in list(re.finditer(r"GH₵[0-9,]+", html))[:3]:
    s = max(0, m.start() - 260)
    print(re.sub(r"\s+", " ", html[s:m.end() + 60]))
    print("  ~~~")

# 3. Distinct class tokens near price/card regions (heuristic: classes used within 400 chars of a price)
price_positions = [m.start() for m in re.finditer(r"GH₵[0-9,]+", html)]
classes = {}
for p in price_positions:
    for cm in re.finditer(r'class="([^"]+)"', html[max(0, p - 500):p + 500]):
        for tok in cm.group(1).split():
            classes[tok] = classes.get(tok, 0) + 1
print("\nCLASSES NEAR PRICES (top 25):")
for tok, n in sorted(classes.items(), key=lambda kv: -kv[1])[:25]:
    print(f"  {n:4d}  {tok}")
