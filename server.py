"""MCP server exposing Garmin Connect data via the garminconnect library."""
import logging
import os
import sys
from datetime import date
from typing import Any

from dotenv import load_dotenv
from garminconnect import Garmin
from mcp.server.fastmcp import FastMCP

load_dotenv()

if os.getenv("GARMIN_DEBUG"):
    # stdout is reserved for the MCP protocol itself, so debug logs go to stderr
    # (or a file if GARMIN_DEBUG_LOG is set) instead.
    handler = (
        logging.FileHandler(os.getenv("GARMIN_DEBUG_LOG"))
        if os.getenv("GARMIN_DEBUG_LOG")
        else logging.StreamHandler(sys.stderr)
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    logging.getLogger("garminconnect").addHandler(handler)
    logging.getLogger("garminconnect").setLevel(logging.DEBUG)

TOKEN_STORE = os.path.expanduser(os.getenv("GARMIN_TOKEN_STORE", "~/.garminconnect"))

mcp = FastMCP(
    "garmin-connect",
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "8000")),
)

_client: Garmin | None = None
_pending_mfa_client: Garmin | None = None


def get_client() -> Garmin:
    """Return the already-authenticated Garmin client, or raise if not logged in yet."""
    if _client is not None:
        return _client
    raise RuntimeError(
        "Not logged in to Garmin Connect yet. Call the login tool first "
        "(and submit_mfa_code afterwards if it asks for one)."
    )


@mcp.tool()
def login() -> dict[str, Any]:
    """Log in to Garmin Connect. Reuses cached tokens in TOKEN_STORE if present,
    otherwise authenticates with GARMIN_EMAIL/GARMIN_PASSWORD. Call this first,
    before any other tool. If the account has MFA enabled, this triggers Garmin
    to send/generate a one-time code and returns status "needs_mfa" — follow up
    with the submit_mfa_code tool.
    """
    global _client, _pending_mfa_client
    if _client is not None:
        return {"status": "already_logged_in", "full_name": _client.get_full_name()}

    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    if not email or not password:
        raise RuntimeError("GARMIN_EMAIL and GARMIN_PASSWORD must be set (e.g. in .env).")

    client = Garmin(email=email, password=password, return_on_mfa=True)
    mfa_status, _ = client.login(TOKEN_STORE)

    if mfa_status == "needs_mfa":
        _pending_mfa_client = client
        return {
            "status": "needs_mfa",
            "message": "Check your email/authenticator app for a Garmin code, "
            "then call submit_mfa_code with it.",
        }

    _client = client
    return {"status": "ok", "full_name": client.get_full_name()}


@mcp.tool()
def submit_mfa_code(code: str) -> dict[str, Any]:
    """Complete a pending Garmin login that is waiting on a multi-factor auth code.

    Call this only after the login tool returned status "needs_mfa". The code
    comes from your email or authenticator app tied to Garmin Connect.

    Args:
        code: The one-time MFA code from Garmin.
    """
    global _client, _pending_mfa_client
    if _pending_mfa_client is None:
        raise RuntimeError("No Garmin login is currently waiting on an MFA code. Call login first.")

    client = _pending_mfa_client
    client.resume_login(None, code)
    client.client.dump(TOKEN_STORE)

    _client = client
    _pending_mfa_client = None
    return {"status": "ok", "full_name": client.get_full_name()}


def _today(d: str | None) -> str:
    return d or date.today().isoformat()


@mcp.tool()
def get_user_profile() -> dict[str, Any]:
    """Get the full name and basic profile info of the logged-in Garmin user."""
    client = get_client()
    return {"full_name": client.get_full_name()}


@mcp.tool()
def get_daily_summary(day: str | None = None) -> dict[str, Any]:
    """Get the daily stats summary (steps, calories, distance, HR, etc.) for a given date.

    Args:
        day: Date in YYYY-MM-DD format. Defaults to today.
    """
    return get_client().get_stats(_today(day))


@mcp.tool()
def get_steps(day: str | None = None) -> Any:
    """Get detailed step count data (per-interval) for a given date.

    Args:
        day: Date in YYYY-MM-DD format. Defaults to today.
    """
    return get_client().get_steps_data(_today(day))


@mcp.tool()
def get_heart_rate(day: str | None = None) -> Any:
    """Get heart rate data (resting, min, max, time series) for a given date.

    Args:
        day: Date in YYYY-MM-DD format. Defaults to today.
    """
    return get_client().get_heart_rates(_today(day))


@mcp.tool()
def get_sleep(day: str | None = None) -> Any:
    """Get sleep data (stages, duration, score) for the night ending on the given date.

    Args:
        day: Date in YYYY-MM-DD format. Defaults to today.
    """
    return get_client().get_sleep_data(_today(day))


@mcp.tool()
def get_body_battery(start_day: str | None = None, end_day: str | None = None) -> Any:
    """Get Body Battery energy level data between two dates.

    Args:
        start_day: Start date in YYYY-MM-DD format. Defaults to today.
        end_day: End date in YYYY-MM-DD format. Defaults to start_day.
    """
    start = _today(start_day)
    end = end_day or start
    return get_client().get_body_battery(start, end)


@mcp.tool()
def get_stress(day: str | None = None) -> Any:
    """Get stress level data for a given date.

    Args:
        day: Date in YYYY-MM-DD format. Defaults to today.
    """
    return get_client().get_stress_data(_today(day))


@mcp.tool()
def get_hrv(day: str | None = None) -> Any:
    """Get heart rate variability (HRV) data for a given date.

    Args:
        day: Date in YYYY-MM-DD format. Defaults to today.
    """
    return get_client().get_hrv_data(_today(day))


@mcp.tool()
def get_body_composition(day: str | None = None) -> Any:
    """Get body composition data (weight, body fat %, muscle mass, etc.) for a given date.

    Args:
        day: Date in YYYY-MM-DD format. Defaults to today.
    """
    return get_client().get_body_composition(_today(day))


@mcp.tool()
def get_activities(limit: int = 10, start: int = 0) -> Any:
    """List recent Garmin activities (workouts/runs/rides/etc.), most recent first.

    Args:
        limit: Max number of activities to return. Defaults to 10.
        start: Offset into the activity list for pagination. Defaults to 0.
    """
    return get_client().get_activities(start, limit)


@mcp.tool()
def get_activities_by_date(start_day: str, end_day: str, activity_type: str | None = None) -> Any:
    """List activities within a date range, optionally filtered by activity type.

    Args:
        start_day: Start date in YYYY-MM-DD format.
        end_day: End date in YYYY-MM-DD format.
        activity_type: Optional Garmin activity type filter (e.g. "running", "cycling").
    """
    return get_client().get_activities_by_date(start_day, end_day, activity_type)


@mcp.tool()
def get_activity_details(activity_id: str) -> Any:
    """Get full details (splits, laps, metrics) for a single activity.

    Args:
        activity_id: The Garmin Connect activity ID, as returned by get_activities.
    """
    return get_client().get_activity(activity_id)


@mcp.tool()
def get_activity_splits(activity_id: str) -> Any:
    """Get lap/split summaries for a single activity.

    Args:
        activity_id: The Garmin Connect activity ID, as returned by get_activities.
    """
    return get_client().get_activity_splits(activity_id)


@mcp.tool()
def get_race_predictions() -> Any:
    """Get Garmin's predicted race times (5K, 10K, half marathon, marathon)."""
    return get_client().get_race_predictions()


@mcp.tool()
def get_training_readiness(day: str | None = None) -> Any:
    """Get the morning training readiness score for a given date.

    Args:
        day: Date in YYYY-MM-DD format. Defaults to today.
    """
    return get_client().get_morning_training_readiness(_today(day))


@mcp.tool()
def get_respiration(day: str | None = None) -> Any:
    """Get respiration rate data for a given date.

    Args:
        day: Date in YYYY-MM-DD format. Defaults to today.
    """
    return get_client().get_respiration_data(_today(day))


@mcp.tool()
def get_spo2(day: str | None = None) -> Any:
    """Get pulse oxygen (SpO2) data for a given date.

    Args:
        day: Date in YYYY-MM-DD format. Defaults to today.
    """
    return get_client().get_spo2_data(_today(day))


@mcp.tool()
def get_devices() -> Any:
    """List Garmin devices registered to the account."""
    return get_client().get_devices()


@mcp.tool()
def get_personal_records() -> Any:
    """Get personal records (fastest times/distances) across all activity types."""
    return get_client().get_personal_record()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
