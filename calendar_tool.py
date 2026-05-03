from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz

from auth_test import get_credentials_for_email


def get_calendar_service(creds):
    return build("calendar", "v3", credentials=creds)


def get_free_busy(service, emails, time_min, time_max, timezone="UTC"):
    body = {
        "timeMin": time_min,
        "timeMax": time_max,
        "timeZone": timezone,
        "items": [{"id": email} for email in emails]
    }
    result = service.freebusy().query(body=body).execute()
    busy_slots = {}
    for email in emails:
        busy_slots[email] = result["calendars"][email].get("busy", [])
    return busy_slots


def get_free_busy_for_participant(email, time_min, time_max, timezone="UTC"):
    creds = get_credentials_for_email(email)
    if not creds:
        return []
    service = get_calendar_service(creds)
    body = {
        "timeMin": time_min,
        "timeMax": time_max,
        "timeZone": timezone,
        "items": [{"id": email}]
    }
    result = service.freebusy().query(body=body).execute()
    return result["calendars"][email].get("busy", [])


def get_multi_participant_busy(participants, time_min, time_max, timezone="UTC",
                               fallback_service=None):
    all_busy = {}
    unauthenticated = []

    for email in participants:
        creds = get_credentials_for_email(email)
        if creds:
            busy = get_free_busy_for_participant(email, time_min, time_max, timezone)
            all_busy[email] = busy
        else:
            unauthenticated.append(email)

    if unauthenticated and fallback_service:
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "timeZone": timezone,
            "items": [{"id": email} for email in unauthenticated]
        }
        result = fallback_service.freebusy().query(body=body).execute()
        for email in unauthenticated:
            cal_data = result["calendars"].get(email, {})
            all_busy[email] = cal_data.get("busy", [])
            errors = cal_data.get("errors", [])
            if errors:
                print(f"   Could not read calendar for {email}: {errors}")

    return all_busy, unauthenticated


def find_free_slots(busy_dict, time_min, time_max, duration_mins=30,
                    timezone="UTC", preferred_time=None, excluded_days=None):
    tz = pytz.timezone(timezone)
    start = datetime.fromisoformat(time_min.replace("Z", "+00:00"))
    end = datetime.fromisoformat(time_max.replace("Z", "+00:00"))

    all_busy = []
    for email, slots in busy_dict.items():
        for slot in slots:
            busy_start = datetime.fromisoformat(slot["start"].replace("Z", "+00:00"))
            busy_end = datetime.fromisoformat(slot["end"].replace("Z", "+00:00"))
            all_busy.append((busy_start, busy_end))

    all_busy.sort(key=lambda x: x[0])
    merged = []
    for block in all_busy:
        if merged and block[0] <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], block[1]))
        else:
            merged.append(list(block))

    raw_free = []
    cursor = start
    for busy_start, busy_end in merged:
        if cursor < busy_start:
            gap_mins = (busy_start - cursor).total_seconds() / 60
            if gap_mins >= duration_mins:
                raw_free.append((cursor, busy_start))
        cursor = max(cursor, busy_end)
    if cursor < end:
        gap_mins = (end - cursor).total_seconds() / 60
        if gap_mins >= duration_mins:
            raw_free.append((cursor, end))

    def in_preferred_window(s):
        hour = s.hour
        if preferred_time == "morning":
            return 9 <= hour < 12
        if preferred_time == "afternoon":
            return 13 <= hour < 17
        return True

    def not_excluded(s):
        if not excluded_days:
            return True
        return s.strftime("%A") not in excluded_days

    return [(s, e) for s, e in raw_free if in_preferred_window(s) and not_excluded(s)]


def create_calendar_event(service, summary, attendees, start_time, end_time, timezone="UTC"):
    event = {
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": timezone},
        "end": {"dateTime": end_time, "timeZone": timezone},
        "attendees": [{"email": email} for email in attendees],
        "conferenceData": {
            "createRequest": {"requestId": "accord-meet-1"}
        }
    }
    result = service.events().insert(
        calendarId="primary",
        body=event,
        conferenceDataVersion=1,
        sendUpdates="all"
    ).execute()
    print(f"Event created: {result.get('htmlLink')}")
    return result