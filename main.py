import asyncio
from fastapi import FastAPI, HTTPException, Body, BackgroundTasks
import uvicorn
from pydantic import BaseModel
from typing import Optional

from scraper.producthunt import ProductHuntScraper
from db.operations import get_all_users, get_all_registration_usernames, update_streak, upsert_user, update_registration_streak

app = FastAPI(
    title="Product Hunt Scraper API",
    description="API to scrape Product Hunt streaks and update the database.",
    version="1.0.0"
)

@app.get("/")
def home():
    import curl_cffi
    return {"message": "Hello from Python Backend", "curl_cffi_version": curl_cffi.__version__}

@app.get("/debug/ph")
async def debug_ph():
    from curl_cffi.requests import AsyncSession
    from scraper.producthunt import _build_url
    import curl_cffi, os
    s = AsyncSession(impersonate="chrome131")
    url = _build_url("rrhoover")
    try:
        r = await s.get(url, timeout=30)
        blocked = "Just a moment" in r.text and "Cloudflare" in r.text
        return {"status": r.status_code, "blocked": blocked, "curl_cffi": curl_cffi.__version__, "via_scraperapi": bool(os.getenv("SCRAPER_API_KEY"))}
    except Exception as e:
        return {"error": str(e), "curl_cffi": curl_cffi.__version__}
    finally:
        await s.close()

class ScrapeRequest(BaseModel):
    username_or_url: str
    debug: bool = False
    full_name: str = ""
    email: str = ""

def clean_username(input_str: str) -> str:
    """Extracts username from a URL or @-handle."""
    input_str = input_str.strip()
    if "/" in input_str:
        input_str = input_str.rstrip("/").split("/")[-1]
    if input_str.startswith("@"):
        input_str = input_str[1:]
    return input_str

async def _scrape_all_background(targets: list):
    """Scrape all users one by one in the background (runs on Railway after 202 response)."""
    scraper = ProductHuntScraper()
    await scraper.start()
    updated = 0
    try:
        for reg in targets:
            uname = reg["producthunt_username"].strip()
            try:
                result = await scraper.scrape_profile(uname)
                if not result:
                    print(f"[scrape/all] No result for @{uname}, skipping")
                    continue

                update_registration_streak(uname, result["current_streak"])

                try:
                    user_id = upsert_user({
                        "full_name": reg.get("full_name") or uname,
                        "email": reg.get("email") or f"{uname}@placeholder.com",
                        "producthunt_username": uname,
                        "producthunt_url": f"https://www.producthunt.com/@{uname}",
                    })
                    update_streak(user_id, result["current_streak"], result["avatar_url"])
                except Exception as e:
                    print(f"[scrape/all] users-table sync failed for @{uname}: {e}")

                updated += 1
                print(f"[scrape/all] @{uname} → streak={result['current_streak']} ({updated}/{len(targets)})")
            except Exception as e:
                print(f"[scrape/all] Error scraping @{uname}: {e}")
    finally:
        await scraper.stop()
        print(f"[scrape/all] Done — {updated}/{len(targets)} updated.")


@app.post("/scrape/all")
async def scrape_all_users_endpoint(background_tasks: BackgroundTasks):
    registrations = get_all_registration_usernames()
    targets = [r for r in registrations if r.get("producthunt_username", "").strip()]

    if not targets:
        return {"message": "No registered users found."}

    background_tasks.add_task(_scrape_all_background, targets)
    return {
        "message": f"Scrape started for {len(targets)} users (running in background, one by one).",
        "count": len(targets),
    }

@app.post("/scrape/single")
async def scrape_single_endpoint(request: ScrapeRequest):
    username = clean_username(request.username_or_url)
    scraper = ProductHuntScraper()
    await scraper.start()

    try:
        result = await scraper.scrape_profile(username, debug=request.debug)
        if result:
            db_status = "skipped"
            try:
                user_id = upsert_user({
                    "full_name": request.full_name or username,
                    "email": request.email or f"{username}@placeholder.com",
                    "producthunt_username": username,
                    "producthunt_url": f"https://www.producthunt.com/@{username}",
                })
                update_streak(user_id, result["current_streak"], result["avatar_url"])
                db_status = "saved"
            except Exception as e:
                db_status = f"error: {str(e)}"
            
            return {
                "username": username,
                "streak": result["current_streak"],
                "avatar_url": result["avatar_url"],
                "db_status": db_status
            }
        else:
            raise HTTPException(status_code=404, detail=f"Failed to scrape @{username}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await scraper.stop()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
