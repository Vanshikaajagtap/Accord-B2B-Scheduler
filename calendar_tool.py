from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz

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

def find_free_slots(busy_dict, time_min, time_max, duration_mins=30, timezone="UTC"):
    
    tz = pytz.timezone(timezone)
    start = datetime.fromisoformat(time_min.replace("Z", "+00:00"))
    end = datetime.fromisoformat(time_max.replace("Z", "+00:00"))

    # Collect all busy intervals across everyone
    all_busy = []
    for email, slots in busy_dict.items():
        for slot in slots:
            busy_start = datetime.fromisoformat(slot["start"].replace("Z", "+00:00"))
            busy_end = datetime.fromisoformat(slot["end"].replace("Z", "+00:00"))
            all_busy.append((busy_start, busy_end))

    # Sort and merge overlapping busy blocks
    all_busy.sort(key=lambda x: x[0])
    merged = []
    for block in all_busy:
        if merged and block[0] <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], block[1]))
        else:
            merged.append(list(block))

    # Find free gaps between busy blocks
    free_slots = []
    cursor = start
    for busy_start, busy_end in merged:
        if cursor < busy_start:
            gap_mins = (busy_start - cursor).total_seconds() / 60
            if gap_mins >= duration_mins:
                free_slots.append((cursor, busy_start))
        cursor = max(cursor, busy_end)

    # Check remaining time after last busy block
    if cursor < end:
        gap_mins = (end - cursor).total_seconds() / 60
        if gap_mins >= duration_mins:
            free_slots.append((cursor, end))

    return free_slots 



#testing testing testing

if __name__ == "__main__":
    from auth_test import get_credentials

    creds = get_credentials()
    service = get_calendar_service(creds)

    
    now = datetime.utcnow().isoformat() + "Z"
    three_days = (datetime.utcnow() + timedelta(days=3)).isoformat() + "Z"
 
    YOUR_EMAIL = "vanshika.m.jagtap@gmail.com"  
    
    busy = get_free_busy(service, [YOUR_EMAIL], now, three_days)
    print("Busy slots:", busy)

    free = find_free_slots(busy, now, three_days, duration_mins=30)
    print(f"\nFree windows ({len(free)} found):")
    for s, e in free:
        print(f"  {s.strftime('%a %b %d %I:%M %p')} → {e.strftime('%I:%M %p')} UTC")