"""Show one full card's feature markup (prop-features region)."""
import re, pathlib

html = (pathlib.Path.home() / "accra-rentals-predictor" / "data" / "raw" / "search-accra-rendered.html").read_text(encoding="utf-8")

# First card wrapper
m = re.search(r'<div class="mqs-prop-dt-wrapper[^"]*">.*?</div>\s*</div>\s*</div>', html, re.S)
snippet = re.sub(r"\s+", " ", m.group(0))
print(snippet[:1400])

# All prop-features regions
print("\n--- prop-features SAMPLE (first 5) ---")
for fm in list(re.finditer(r'<div class="prop-features">(.*?)</div>', html, re.S))[:5]:
    print(re.sub(r"\s+", " ", fm.group(1))[:200])
    print("  ~~~")
