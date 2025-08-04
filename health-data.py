
from datetime import datetime, timezone
from garminconnect import Garmin
from notion_client import Client
from dotenv import load_dotenv
import pytz
import os
import sys

LOCAL_TZ = pytz.timezone("America/New_York")

def iso_today():
    return datetime.now(tz=LOCAL_TZ).strftime("%Y-%m-%d")

def format_name(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("%d.%m.%Y")
    except Exception:
        return date_str or "Unknown"

def login_to_garmin():
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    token_store = os.path.expanduser(os.getenv("GARMIN_TOKEN_STORE", "~/.garmin_tokens"))
    g = Garmin(email, password)
    try:
        if os.path.exists(token_store):
            print(f"Using stored tokens from {token_store}")
            g.login(tokenstore=token_store)
        else:
            print("No token store found — performing initial login.")
            g.login()
            if hasattr(g, "garth") and g.garth:
                os.makedirs(os.path.dirname(token_store), exist_ok=True)
                g.garth.save(token_store)
                print(f"Saved tokens to {token_store}")
        return g
    except Exception as e:
        print(f"Garmin login failed: {e}")
        sys.exit(1)

def fetch_today_health(garmin, date_str):
    weight = None
    bmi = None
    rhr = None
    date_from_data = None

    try:
        daily = garmin.get_daily_summary(date_str)
        if isinstance(daily, dict):
            rhr = daily.get("restingHeartRate") or daily.get("restingHr")
    except Exception as e:
        print(f"Note: couldn't read resting HR for {date_str}: {e}")

    try:
        body = garmin.get_body_composition(date_str)
        if isinstance(body, dict) and body:
            date_from_data = body.get("calendarDate") or body.get("date") or date_str
            weight = (
                body.get("weight")
                or body.get("weightKilograms")
                or body.get("weight_kg")
            )
            bmi = body.get("bmi") or body.get("bodyMassIndex")
    except Exception as e:
        print(f"Note: couldn't read body composition for {date_str}: {e}")

    if weight is None and bmi is None and rhr is None:
        return None

    return {
        "calendarDate": date_from_data or date_str,
        "weight": weight if (weight is not None) else 0,
        "restingHeartRate": rhr if (rhr is not None) else 0,
        "bmi": bmi if (bmi is not None) else 0,
    }

def notion_row_exists(notion, database_id, date_str):
    try:
        res = notion.databases.query(
            database_id=database_id,
            filter={"property": "Date", "date": {"equals": date_str}},
        )
        return len(res.get("results", [])) > 0
    except Exception as e:
        print(f"Warning: Notion query failed: {e}")
        return False

def create_health_row(notion, database_id, payload):
    props = {
        "Name": {"title": [{"text": {"content": format_name(payload["calendarDate"])}}]},
        "Date": {"date": {"start": payload["calendarDate"]}},
        "Weight": {"number": payload.get("weight", 0)},
        "Resting HR": {"number": payload.get("restingHeartRate", 0)},
        "BMI": {"number": payload.get("bmi", 0)},
    }
    notion.pages.create(parent={"database_id": database_id}, properties=props, icon={"emoji": "🩺"})
    print(f"✅ Added health data for {payload['calendarDate']}")

def create_no_data_placeholder(notion, database_id, date_str):
    props = {
        "Name": {"title": [{"text": {"content": f"No data on {format_name(date_str)}"}}]},
        "Date": {"date": {"start": date_str}},
    }
    notion.pages.create(parent={"database_id": database_id}, properties=props, icon={"emoji": "❌"})
    print(f"⚠️ No health data available for {date_str}")

def main():
    load_dotenv()
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_HEALTH_DB_ID")
    notion = Client(auth=notion_token)
    date_str = iso_today()
    garmin = login_to_garmin()
    health_data = fetch_today_health(garmin, date_str)
    if notion_row_exists(notion, database_id, date_str):
        print(f"Row for {date_str} already exists in Notion. Skipping.")
        return
    if health_data:
        create_health_row(notion, database_id, health_data)
    else:
        create_no_data_placeholder(notion, database_id, date_str)

if __name__ == "__main__":
    main()
