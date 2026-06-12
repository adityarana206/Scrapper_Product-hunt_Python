import re
import asyncio
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup
import logging

class ProductHuntScraper:
    def __init__(self):
        self.session = None

    async def start(self):
        self.session = AsyncSession(impersonate="chrome120")

    async def stop(self):
        if self.session:
            await self.session.close()

    async def scrape_profile(self, username: str, debug: bool = False) -> dict | None:
        url = f"https://www.producthunt.com/@{username}"
        try:
            if not self.session:
                self.session = AsyncSession(impersonate="chrome120")
            
            response = await self.session.get(url, timeout=15)
            if response.status_code != 200:
                print(f"[scraper] Received status code {response.status_code} for @{username}")
                return None

            html = response.text
            if "Just a moment" in html and "Cloudflare" in html:
                print(f"[scraper] Blocked by Cloudflare for @{username}")
                return None

            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(separator=' ', strip=True)

            if debug:
                print(f"[debug] Body preview for @{username}:\n{text[:500]}")

            streak = self._extract_streak(text)
            avatar_url = self._extract_avatar(soup, username)

            return {
                "producthunt_username": username,
                "current_streak": streak,
                "avatar_url": avatar_url,
            }
        except Exception as e:
            print(f"[scraper] Error scraping @{username}: {e}")
            return None

    def _extract_streak(self, text: str) -> int:
        patterns = [
            r"(\d+)\s*day\s*streak",
            r"streak\s*:?\s*(\d+)",
            r"(\d+)\s*days?\s*streak",
            r"(\d+)\s*streak",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 0

    def _extract_avatar(self, soup: BeautifulSoup, username: str) -> str | None:
        for img in soup.find_all("img"):
            alt = img.get("alt", "").lower()
            src = img.get("src", "")
            if src.startswith("http") and ("avatar" in alt or "profile" in alt or username.lower() in alt):
                return src
        
        # Fallback to first valid image
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src.startswith("http"):
                return src
        return None

    async def scrape_batch(self, usernames: list[str]) -> list[dict]:
        results = []
        chunk_size = 5
        for i in range(0, len(usernames), chunk_size):
            chunk = usernames[i:i + chunk_size]
            tasks = [self.scrape_profile(u) for u in chunk]
            chunk_results = await asyncio.gather(*tasks)
            results.extend([r for r in chunk_results if r is not None])
            if i + chunk_size < len(usernames):
                await asyncio.sleep(1) # Be nice to the server
        return results
