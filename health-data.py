from datetime import datetime
from typing import Optional

from notion_client import Client
from dotenv import load_dotenv
import os

# Import your fetch_today_health function. Adjust the import path if necessary.
# from health_data import fetch_today_health


def write_health_to_notion(health: dict, database_id: str, notion_token: str) -> None:
    """
    Create a new page in Notion with the provided health metrics.

    :param health: Dictionary returned by fetch_today_health with keys
                   'calendarDate', 'weight', 'restingHeartRate', 'bmi',
                   'no_data', and 'time'.
    :param database_id: The Notion database ID where the page should be created.
    :param notion_token: An integration token generated from Notion.
    """
    client = Client(auth=notion_token)

    # Format a human‑readable title for the page (e.g. "05.08.2025" or "No data on 04.08.2025").
    date_iso = health.get("calendarDate")
    try:
        dt_obj = datetime.strptime(date_iso, "%Y-%m-%d")
        formatted_date = dt_obj.strftime("%d.%m.%Y")
    except Exception:
        formatted_date = date_iso

    if health.get("no_data"):
        title = f"No data on {formatted_date}"
        icon = {"emoji": "❌"}
    else:
        title = formatted_date
        icon = {"emoji": "💓"}

    # Build the Notion properties payload. Adjust property names to match your Notion DB.
    properties = {
        # Title property – Notion expects the title under a 'title' key
        "Date": {"title": [{"text": {"content": title}}]},
        # Separate Date property (type date) to allow filtering/sorting in Notion
        "Full Date": {"date": {"start": date_iso}},
        "Weight": {"number": health.get("weight", 0.0)},
        "BMI": {"number": health.get("bmi", 0.0)},
        "Resting HR": {"number": health.get("restingHeartRate", 0)},
        "Time": {"rich_text": [{"text": {"content": health.get("time", "")}}]},
        "No Data": {"checkbox": bool(health.get("no_data"))},
    }

    # Create the page in Notion
    client.pages.create(
        parent={"database_id": database_id},
        properties=properties,
        icon=icon,
    )


def main() -> None:
    """
    Example entry point: fetch health data for today and write it to Notion.
    Ensure that GARMIN_EMAIL/GARMIN_PASSWORD and NOTION_TOKEN are set in your
    environment, along with NOTION_HEALTH_DB_ID. Replace the fetch_today_health
    call with your existing Garmin authentication logic.
    """
    load_dotenv()

    notion_token = os.environ.get("NOTION_TOKEN")
    database_id = os.environ.get("NOTION_HEALTH_DB_ID")

    if not notion_token:
        raise RuntimeError("NOTION_TOKEN environment variable is not set")
    if not database_id:
        raise RuntimeError("NOTION_HEALTH_DB_ID environment variable is not set")

    # TODO: authenticate to Garmin and fetch today’s health data
    # For example:
    # garmin = login_to_garmin()  # your custom login function
    # health = fetch_today_health(garmin, datetime.today().strftime("%Y-%m-%d"))

    # For demonstration, use a placeholder health record. Replace this with real data.
    health = {
        "calendarDate": datetime.today().strftime("%Y-%m-%d"),
        "weight": 0.0,
        "restingHeartRate": 0,
        "bmi": 0.0,
        "no_data": True,
        "time": datetime.now().strftime("%H:%M"),
    }

    write_health_to_notion(health, database_id, notion_token)


if __name__ == "__main__":
    main()
