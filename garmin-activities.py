from datetime import datetime, timezone
from garminconnect import Garmin
from notion_client import Client
from dotenv import load_dotenv
import pytz
import os
import json
import garth

# -----------------------------
# Load environment
# -----------------------------
load_dotenv()

GARMIN_EMAIL = os.getenv("GARMIN_EMAIL")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")
TOKEN_STORE = os.path.expanduser(os.getenv("GARMIN_TOKEN_STORE", "~/.garmin_tokens"))

LOCAL_TZ = pytz.timezone("America/Toronto")

# -----------------------------
# Ensure tokens exist (bootstrap via garth if missing)
# -----------------------------
def ensure_garmin_tokens():
    if os.path.exists(TOKEN_STORE):
        print(f"🔐 Using existing token store at {TOKEN_STORE}")
        return

    if not GARMIN_EMAIL or not GARMIN_PASSWORD:
        raise RuntimeError("Missing GARMIN_EMAIL or GARMIN_PASSWORD in .env")

    print("🪪 No token store found — performing initial login with garth and saving tokens...")
    # garth handles SSO + 2FA flows and produces tokens that garminconnect can reuse
    garth.login(GARMIN_EMAIL, GARMIN_PASSWORD)
    os.makedirs(os.path.dirname(TOKEN_STORE), exist_ok=True)
    garth.save(TOKEN_STORE)
    print(f"✅ Saved tokens to {TOKEN_STORE}")

# -----------------------------
# Garmin init (uses token store)
# -----------------------------
def init_garmin_client():
    ensure_garmin_tokens()
    garmin = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
    garmin.login(tokenstore=TOKEN_STORE)
    return garmin

# -----------------------------
# Minimal example main (replace with your sync logic)
# -----------------------------
def main():
    if not NOTION_TOKEN or not NOTION_DB_ID:
        raise RuntimeError("Missing NOTION_TOKEN or NOTION_DB_ID in .env")

    garmin = init_garmin_client()
    client = Client(auth=NOTION_TOKEN)

    # Example: fetch last 5 activities
    activities = garmin.get_activities(0, 5)
    for a in activities:
        print(a.get('startTimeLocal'), a.get('activityName'), a.get('distance'))

if __name__ == "__main__":
    main()
