import re
import os
import asyncio
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY", "")

def _build_url(username: str) -> str:
    ph_url = f"https://www.producthunt.com/@{username}"
    if SCRAPER_API_KEY:
        return f"https://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={ph_url}&render=false"
    return ph_url

class ProductHuntScraper:
    def __init__(self):
        self.session = None

    async def start(self):
        self.session = AsyncSession(impersonate="chrome131")

    async def stop(self):
        if self.session:
            await self.session.close()

    async def scrape_profile(self, username: str, debug: bool = False) -> dict | None:
        url = _build_url(username)
        try:
            if not self.session:
                self.session = AsyncSession(impersonate="chrome131")

            response = await self.session.get(url, timeout=30)
            if response.status_code != 200:
                print(f"[scraper] Received status code {response.status_code} for @{username}")
                return None

            html = response.text
            if "Just a moment" in html and "Cloudflare" in html:
                print(f"[scraper] Blocked by Cloudflare for @{username}")
                return None

            soup = BeautifulSoup(html, "html.parser")

            if debug:
                print(f"[debug] Body preview for @{username}:\n{soup.get_text(separator=' ', strip=True)[:500]}")

            streak = self._extract_streak(soup)
            avatar_url = self._extract_avatar(soup)

            return {
                "producthunt_username": username,
                "current_streak": streak,
                "avatar_url": avatar_url,
            }
        except Exception as e:
            print(f"[scraper] Error scraping @{username}: {e}")
            return None

    def _extract_streak(self, soup: BeautifulSoup) -> int:
        streak_link = soup.find("a", href=lambda h: h and "visit-streaks" in h and "profile_page" in h)
        if streak_link:
            m = re.search(r"(\d+)", streak_link.get_text(separator=" ", strip=True))
            if m:
                return int(m.group(1))
            return 0

        text = soup.get_text(separator=" ", strip=True)
        for pattern in [r"🔥\s*(\d+)\s*day\s*streak", r"(\d+)\s*days?\s+streak", r"(\d+)\s*day\s*streak"]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return int(m.group(1))
        return 0

    def _extract_avatar(self, soup: BeautifulSoup) -> str | None:
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if "ph-avatars.imgix.net" in src:
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
                await asyncio.sleep(1)
        return results
