import asyncio
from scraper.producthunt import ProductHuntScraper

async def run():
    scraper = ProductHuntScraper()
    await scraper.start()
    users = ['rohit_kushwaha18', 'stellera', 'satwik_hiremath']
    for u in users:
        res = await scraper.scrape_profile(u)
        print(u, res)
    await scraper.stop()

asyncio.run(run())
