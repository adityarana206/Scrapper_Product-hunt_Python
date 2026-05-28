import asyncio
from scraper.producthunt import ProductHuntScraper

async def test():
    scraper = ProductHuntScraper()
    await scraper.start()
    res = await scraper.scrape_batch(["raviginfo", "ryanhoover", "producthunt"])
    print(res)
    await scraper.stop()

asyncio.run(test())
