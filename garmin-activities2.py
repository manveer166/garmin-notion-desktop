# activities-data.py
from datetime import datetime
from garminconnect import Garmin
from notion_client import Client
from dotenv import load_dotenv, dotenv_values
import pytz
import os
import sys

# -----------------------------
# Constants / Config
# -----------------------------
# London timezone as requested
local_tz = pytz.timezone("Europe/London")

# Load environment variables
load_dotenv()
CONFIG = dotenv_values()

# Use your provided Activities DB ID, but allow override via env NOTION_DB_ID
DEFAULT_NOTION_ACTIVITIES_DB = "244ef489a270818c9872d834c5f30430"

# -----------------------------
# Helpers
# -----------------------------
def format_pace(average_speed_mps: float) -> str:
    """
    Convert speed (m/s) to mm:ss per km pace text. Returns "" if speed is invalid.
    """
    if not average_speed_mps or average_speed_mps <= 0:
        return ""
    # pace (min/km) = 1000 meters / (speed m/s) / 60
    pace_min = 1000.0 / (average_speed_mps * 60.0)
    minutes = int(pace_min)
    seconds = int(round((pace_min - minutes) * 60))
    if seconds == 60:
        minutes += 1
        seconds = 0
    return f"{minutes}:{seconds:02d} min/km"

def fmt_dt_readable(iso_str: str) -> str:
    """
    Convert an ISO GMT/Local time from Garmin into a local (London) HH:MM string, if possible.
    Fallback to original or 'Unknown'.
    """
    if not iso_str:
        return "Unknown"
    try:
        # Garmin returns e.g. '2025-08-05T07:12:34.0' (local) or '2025-08-05T06:12:34.0' (GMT)
        # Try parse with fromisoformat; assume naive is local time already
        dt = datetime.fromisoformat(iso_str.replace("Z", "").replace("000Z", ""))
        if dt.tzinfo is None:
            # Treat as naive local time, attach local tz
            dt = local_tz.localize(dt)
        # Convert to local_tz explicitly (no-op if already local)
        dt_local = dt.astimezone(local_tz)
        return dt_local.strftime("%H:%M")
    except Exception:
        return "Unknown"

def km(distance_meters) -> float:
    try:
        return round((distance_meters or 0) / 1000.0, 2)
    except Exception:
        return 0.0

def minutes(duration_seconds) -> float:
    try:
        return round((duration_seconds or 0) / 60.0, 2)
    except Exception:
        return 0.0

# -----------------------------
# Notion helpers
# -----------------------------
def activity_exists(client: Client, database_id: str, date_iso: str, activity_name: str):
    """
    Checks if an activity row already exists for the same date and name.
    Assumes:
      - Date property is named 'Date' (date)
      - Title property is 'Activity Name'
    """
    query = client.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {"property": "Date", "date": {"equals": date_iso.split("T")[0]}},
                {"property": "Activity Name", "title": {"equals": activity_name or ""}},
            ]
        }
    )
    results = query.get("results", [])
    return results[0] if results else None

def upsert_activity(client: Client, database_id: str, a: dict):
    """
    Creates (or updates) a Notion page for a Garmin activity dict.
    Expects Garmin activity fields similar to garminconnect get_activities().
    """
    # Extract fields
    start_gmt = a.get("startTimeGMT") or a.get("startTimeLocal")
    start_local_readable = fmt_dt_readable(a.get("startTimeLocal") or a.get("startTimeGMT"))
    date_for_notion = (a.get("startTimeGMT") or a.get("startTimeLocal") or "")[:10]
    name = a.get("activityName") or "Unnamed Activity"
    type_key = (a.get("activityType") or {}).get("typeKey", "Unknown").replace("_", " ").title()
    dist_km = km(a.get("distance"))
    dur_min = minutes(a.get("duration"))
    cals = round(a.get("calories") or 0)
    pace_txt = format_pace(a.get("averageSpeed"))

    # Does it already exist?
    existing = activity_exists(client, database_id, start_gmt or date_for_notion, name)

    # Build properties payload
    props = {
        "Date": {"date": {"start": date_for_notion}},
        #"Start": {"rich_text": [{"text": {"content": start_local_readable}}]},
        "Activity Name": {"title": [{"text": {"content": name}}]},
        # Try select if your DB uses a select property; otherwise Notion API will accept rich_text fallback
        "Activity Type": {"select": {"name": type_key}},
        "Distance (km)": {"number": dist_km},
        "Duration (min)": {"number": dur_min},
        "Calories": {"number": cals},
        "Avg Pace": {"rich_text": [{"text": {"content": pace_txt}}]},
    }

    if existing:
        client.pages.update(page_id=existing["id"], properties=props)
        print(f"Updated: {date_for_notion} · {name}")
    else:
        client.pages.create(parent={"database_id": database_id}, properties=props, icon={"emoji": "🏃"})
        print(f"Created: {date_for_notion} · {name}")

# -----------------------------
# Garmin login (token store like sleep-data.py)
# -----------------------------
def login_to_garmin():
    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")
    token_store = os.getenv("GARMIN_TOKEN_STORE", "~/.garmin_tokens")
    token_store = os.path.expanduser(token_store)
    mfa_code = os.getenv("GARMIN_MFA_CODE")  # Optional, for non-interactive 2FA

    if not garmin_email or not garmin_password:
        print("Missing GARMIN_EMAIL or GARMIN_PASSWORD")
        sys.exit(1)

    garmin = Garmin(garmin_email, garmin_password)

    try:
        if os.path.exists(token_store):
            print(f"Using stored tokens from {token_store}")
            garmin.login(tokenstore=token_store)
            return garmin

        if mfa_code:
            print("Using non-interactive 2FA flow")
            client_state, _ = garmin.login(return_on_mfa=True)
            if client_state == "needs_mfa":
                garmin.resume_login(client_state, mfa_code)
            else:
                print("MFA was expected but not requested (continuing).")
        else:
            garmin.login()

        if hasattr(garmin, "garth") and garmin.garth:
            os.makedirs(os.path.dirname(token_store), exist_ok=True)
            garmin.garth.save(token_store)
            print(f"Saved authentication tokens to {token_store}")

        return garmin
    except Exception as e:
        print(f"Error during Garmin login: {e}")
        sys.exit(1)

# -----------------------------
# Main
# -----------------------------
def main():
    notion_token = os.getenv("NOTION_TOKEN")
    if not notion_token:
        print("Missing NOTION_TOKEN")
        sys.exit(1)

    # Allow override via env NOTION_DB_ID; otherwise use your provided ID
    database_id = os.getenv("NOTION_DB_ID", DEFAULT_NOTION_ACTIVITIES_DB)

    # Login + clients
    garmin = login_to_garmin()
    client = Client(auth=notion_token)

    # Fetch a reasonable batch (adjust as you wish)
    try:
        activities = garmin.get_activities(0, 30)
    except Exception as e:
        print(f"No activities available or error fetching activities: {e}")
        # If you want to create a placeholder row in Notion when nothing is found, uncomment below:
        # client.pages.create(
        #     parent={"database_id": database_id},
        #     properties={
        #         "Date": {"date": {"start": datetime.now(local_tz).strftime("%Y-%m-%d")}},
        #         "Activity Name": {"title": [{"text": {"content": "No activities found"}}]},
        #     },
        #     icon={"emoji": "❌"},
        # )
        sys.exit(0)

    if not activities:
        print("No activities found.")
        # (Optional) create a placeholder page as above
        sys.exit(0)

    for a in activities:
        upsert_activity(client, database_id, a)

if __name__ == "__main__":
    main()
