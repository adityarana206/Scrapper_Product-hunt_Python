import re
from bs4 import BeautifulSoup

with open("debug.html", "r") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
text = soup.get_text(separator=' ', strip=True)

match = re.search(r"(\d+)\s*day\s*streak", text, re.IGNORECASE)
if match:
    print("Found streak:", match.group(1))
else:
    print("Streak not found in text.")
    print("Preview of text:", text[:1000])

imgs = soup.find_all("img")
for img in imgs:
    print("IMG:", img.get("src"), img.get("alt"))

