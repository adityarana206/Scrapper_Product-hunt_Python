import re
import asyncio
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup

class ProductHuntScraper:
    def __init__(self):
        self.session = None

    async def start(self):
        self.session = AsyncSession(impersonate="chrome131")

    async def stop(self):
        if self.session:
            await self.session.close()

    async def scrape_profile(self, username: str, debug: bool = False) -> dict | None:
        url = f"https://www.producthunt.com/@{username}"
        try:
            if not self.session:
                self.session = AsyncSession(impersonate="chrome131")

            response = await self.session.get(url, timeout=20)

            if response.status_code == 404:
                print(f"[scraper] @{username} not found (404)")
                return None

            if response.status_code != 200:
                print(f"[scraper] HTTP {response.status_code} for @{username}")
                return None

            html = response.text

            if "Just a moment" in html and "Cloudflare" in html:
                print(f"[scraper] Cloudflare challenge for @{username}")
                return None

            # Minimal sanity check — logged-out profile pages always contain this
            if "producthunt.com" not in html:
                print(f"[scraper] Unexpected response for @{username}")
                return None

            soup = BeautifulSoup(html, "html.parser")

            if debug:
                text = soup.get_text(separator=" ", strip=True)
                print(f"[debug] @{username} text preview:\n{text[:600]}")

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
        # Primary: the profile streak is inside <a href="/visit-streaks?ref=profile_page">.
        # There is also a nav link with the same base path but ref=header_nav that has no number,
        # so we must match specifically on "profile_page".
        streak_link = soup.find("a", href=lambda h: h and "visit-streaks" in h and "profile_page" in h)
        if streak_link:
            link_text = streak_link.get_text(separator=" ", strip=True)
            m = re.search(r"(\d+)", link_text)
            if m:
                return int(m.group(1))
            return 0

        # Fallback: regex on visible page text (handles future PH HTML changes)
        text = soup.get_text(separator=" ", strip=True)
        for pattern in [
            r"🔥\s*(\d+)\s*day\s*streak",
            r"(\d+)\s*days?\s+streak",
        ]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return int(m.group(1))

        # No streak → user has no active streak
        return 0

    def _extract_avatar(self, soup: BeautifulSoup) -> str | None:
        # All Product Hunt user avatars are served from ph-avatars.imgix.net.
        # The first matching img is always the profile picture (appears before badge images).
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
                await asyncio.sleep(1.5)
        return results
