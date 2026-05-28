from curl_cffi import requests

response = requests.get("https://www.producthunt.com/@raviginfo", impersonate="chrome110")
print("Status Code:", response.status_code)
body = response.text
with open("debug.html", "w") as f:
    f.write(body)

if "Just a moment" in body or "Cloudflare" in body:
    print("Blocked by Cloudflare")
else:
    print("Success! Got the page.")

