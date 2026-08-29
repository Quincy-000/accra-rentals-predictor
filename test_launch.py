from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")

driver = webdriver.Chrome(options=options)
driver.get("https://meqasa.com")
print("Page title:", driver.title)
driver.quit()
