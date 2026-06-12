import asyncio
from fastapi import FastAPI, HTTPException, Body
import uvicorn
from pydantic import BaseModel
from typing import Optional

from scraper.producthunt import ProductHuntScraper
from db.operations import get_all_users, get_all_registration_usernames, update_streak, upsert_user

app = FastAPI(
    title="Product Hunt Scraper API",
    description="API to scrape Product Hunt streaks and update the database.",
    version="1.0.0"
)

@app.get("/")
def home():
    return {"message": "Hello from Python Backend"}

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

@app.post("/scrape/all")
async def scrape_all_users_endpoint():
    scraper = ProductHuntScraper()
    await scraper.start()

    try:
        users = get_all_users()
        existing_usernames = {u["producthunt_username"] for u in users if u.get("producthunt_username")}

        # Also include registered students not yet in the users table
        registrations = get_all_registration_usernames()
        for reg in registrations:
            uname = reg.get("producthunt_username", "").strip()
            if uname and uname not in existing_usernames:
                new_id = upsert_user({
                    "full_name": reg.get("full_name") or uname,
                    "email": reg.get("email") or f"{uname}@placeholder.com",
                    "producthunt_username": uname,
                    "producthunt_url": f"https://www.producthunt.com/@{uname}",
                })
                existing_usernames.add(uname)

        # Re-fetch users so we have IDs for all (including newly upserted ones)
        users = get_all_users()
        if not users:
            return {"message": "No users found in database."}

        usernames = [u["producthunt_username"] for u in users if u.get("producthunt_username")]

        results = await scraper.scrape_batch(usernames)
        updated_count = 0
        updated_users = []

        for r in results:
            user = next((u for u in users if u["producthunt_username"] == r["producthunt_username"]), None)
            if user:
                update_streak(user["id"], r["current_streak"], r["avatar_url"])
                updated_count += 1
                updated_users.append({
                    "username": r["producthunt_username"],
                    "streak": r["current_streak"],
                    "avatar_url": r["avatar_url"]
                })

        return {
            "message": f"Successfully updated {updated_count} users.",
            "updated_users": updated_users
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await scraper.stop()

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
