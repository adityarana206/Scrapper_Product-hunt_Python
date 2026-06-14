from datetime import datetime, timezone
from db.supabase_client import get_supabase


def get_all_users():
    supabase = get_supabase()
    result = supabase.table("users").select("*").execute()
    return result.data


def get_all_registration_usernames():
    supabase = get_supabase()
    result = supabase.table("registrations").select("producthunt_username, full_name, email").execute()
    return result.data or []


def get_users_needing_update(hours_threshold: int = 24):
    supabase = get_supabase()
    result = supabase.table("users").select("*").execute()
    now = datetime.now(timezone.utc)
    stale = []
    for user in result.data:
        last = user.get("last_updated")
        if last is None:
            stale.append(user)
        else:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if (now - last_dt).total_seconds() > hours_threshold * 3600:
                stale.append(user)
    return stale


def upsert_user(user_data: dict):
    supabase = get_supabase()
    existing = (
        supabase.table("users")
        .select("id")
        .eq("producthunt_username", user_data["producthunt_username"])
        .execute()
    )
    if existing.data:
        user_id = existing.data[0]["id"]
        supabase.table("users").update(user_data).eq("id", user_id).execute()
        return user_id
    else:
        result = supabase.table("users").insert(user_data).execute()
        return result.data[0]["id"]


def update_streak(user_id: str, streak_count: int, avatar_url: str | None):
    supabase = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    user = supabase.table("users").select("highest_streak").eq("id", user_id).execute()
    current_highest = user.data[0]["highest_streak"] if user.data else 0
    highest = max(current_highest, streak_count)

    update = {
        "current_streak": streak_count,
        "highest_streak": highest,
        "last_updated": now,
    }
    if avatar_url:
        update["avatar_url"] = avatar_url

    supabase.table("users").update(update).eq("id", user_id).execute()

    supabase.table("streak_history").insert({
        "user_id": user_id,
        "streak_count": streak_count,
        "captured_at": now,
    }).execute()

    return streak_count


def update_registration_streak(producthunt_username: str, streak_count: int):
    supabase = get_supabase()

    reg = supabase.table("registrations").select("id, highest_streak").eq("producthunt_username", producthunt_username).execute()
    if not reg.data:
        return

    reg_id = reg.data[0]["id"]
    current_highest = reg.data[0].get("highest_streak") or 0
    highest = max(current_highest, streak_count)

    supabase.table("registrations").update({
        "current_streak": streak_count,
        "highest_streak": highest,
    }).eq("id", reg_id).execute()


def bulk_insert_users(users: list[dict]):
    supabase = get_supabase()
    result = supabase.table("users").upsert(
        users, on_conflict="email", ignore_duplicates=False
    ).execute()
    return result.data
