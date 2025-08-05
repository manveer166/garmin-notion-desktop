def fetch_today_health(garmin, date_str):
    """
    Collect weight, BMI, and resting HR for a given YYYY-MM-DD.
    Works across garminconnect versions by trying multiple endpoints.
    """
    weight = None
    bmi = None
    rhr = None
    date_from_data = None

    # --- Resting HR ---
    for method in ("get_stats", "get_user_summary"):
        try:
            fn = getattr(garmin, method, None)
            if fn:
                stats = fn(date_str) or {}
                # common keys seen across versions
                rhr = (
                    stats.get("restingHeartRate")
                    or stats.get("restingHr")
                    or stats.get("resting_heart_rate")
                )
                if rhr:
                    break
        except Exception as e:
            print(f"Note: couldn't read RHR via {method} for {date_str}: {e}")

    # --- Body composition (weight / BMI) ---
    # Some versions return a dict, others a list of logs.
    for method in ("get_body_composition", "get_body_composition_logs"):
        try:
            fn = getattr(garmin, method, None)
            if not fn:
                continue
            body = fn(date_str)
            if not body:
                continue

            # Normalize to a single dict "entry"
            if isinstance(body, list):
                # choose the last/most recent entry for that date
                entry = body[-1]
            elif isinstance(body, dict):
                entry = body
            else:
                entry = {}

            date_from_data = (
                entry.get("calendarDate") or entry.get("date") or date_str
            )
            weight = (
                entry.get("weight")
                or entry.get("weightKilograms")
                or entry.get("weight_kg")
            )
            bmi = entry.get("bmi") or entry.get("bodyMassIndex")

            # If we got either, we’re done
            if weight is not None or bmi is not None:
                break
        except Exception as e:
            print(f"Note: couldn't read body composition via {method} for {date_str}: {e}")

    if weight is None and bmi is None and rhr is None:
        return None

    return {
        "calendarDate": date_from_data or date_str,
        "weight": float(weight) if weight is not None else 0.0,
        "restingHeartRate": int(rhr) if rhr is not None else 0,
        "bmi": float(bmi) if bmi is not None else 0.0,
    }
