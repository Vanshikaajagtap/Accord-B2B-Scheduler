from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import TypedDict, List
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

from auth_test import get_credentials, is_email_authenticated
from calendar_tool import (get_calendar_service, get_multi_participant_busy,
                           find_free_slots)
from gmail_tool import get_gmail_service, create_draft

load_dotenv()

class AccordState(TypedDict):
    raw_request: str
    participants: List[str]
    duration_mins: int
    timeframe_days: int
    timezone: str
    preferred_time: str
    excluded_days: List[str]
    free_slots: List[dict]
    draft_reply: str
    retry_count: int
    is_compromise: bool
    unauthenticated_participants: List[str]
    target_date: str

llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)


def parse_request(state: AccordState) -> AccordState:
    print("\nParsing request...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""
You are a scheduling assistant. Extract structured info from this request.
Return ONLY valid JSON, no explanation.

Current Date: {current_date}
Request: "{state['raw_request']}"

Handle these edge cases carefully:
- If a specific date is mentioned (like "12th may"), set "target_date" to that date in "YYYY-MM-DD" format. 
- Otherwise, set "target_date" to null and use "timeframe_days" (e.g. "next week" = 7, default = 5).
- "morning" = preferred_time: "morning"
- "afternoon" = preferred_time: "afternoon"
- "not Mondays" or "avoid Fridays" = excluded_days: ["Monday"]
- "30 mins" or "half hour" or "quick call" = duration_mins: 30
- "an hour" = duration_mins: 60
- multiple emails mentioned = all go in participants list
- timezone: MUST be a standard IANA timezone identifier (e.g., "America/New_York", "Asia/Kolkata", "Europe/London"). NEVER return abbreviations like "IST" or "EST". If none mentioned = default "UTC".
- if no duration mentioned = default 30

Return exactly:
{{
  "participants": ["email@example.com"],
  "duration_mins": 30,
  "timeframe_days": 7,
  "timezone": "UTC",
  "preferred_time": "any",
  "excluded_days": [],
  "target_date": null
}}
"""
    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = content[0]["text"] if isinstance(content[0], dict) else content[0]
    content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    parsed = json.loads(content)

    print(f"   Participants: {parsed['participants']}")
    print(f"   Duration: {parsed['duration_mins']} mins")
    print(f"   Looking {parsed['timeframe_days']} days ahead")

    return {
        **state,
        "participants": parsed["participants"],
        "duration_mins": parsed["duration_mins"],
        "timeframe_days": parsed["timeframe_days"],
        "timezone": parsed["timezone"],
        "preferred_time": parsed.get("preferred_time", "any"),
        "excluded_days": parsed.get("excluded_days", []),
        "target_date": parsed.get("target_date"),
    }


def fetch_availability(state: AccordState) -> AccordState:
    print("\nFetching availability for all participants...")
    creds = get_credentials()
    fallback_service = get_calendar_service(creds)

    if state.get("target_date"):
        target_dt = datetime.fromisoformat(state["target_date"])
        now = target_dt.isoformat() + "Z"
        future = (target_dt + timedelta(days=1)).isoformat() + "Z"
        print(f"   Target date specified: {state['target_date']}")
    else:
        days = state["timeframe_days"] + (state["retry_count"] * 3)
        now = datetime.utcnow().isoformat() + "Z"
        future = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"

    participants = state["participants"]

    for email in participants:
        auth_status = "authenticated" if is_email_authenticated(email) else "not authenticated (using fallback)"
        print(f"   {email}: {auth_status}")

    busy, unauthenticated = get_multi_participant_busy(
        participants, now, future, state["timezone"],
        fallback_service=fallback_service
    )

    print(f"   Checked {len(busy)} participant calendars")
    if unauthenticated:
        print(f"   Unauthenticated (fallback used): {unauthenticated}")

    free = find_free_slots(
        busy, now, future,
        state["duration_mins"],
        state["timezone"],
        preferred_time=state.get("preferred_time"),
        excluded_days=state.get("excluded_days")
    )

    print(f"   Found {len(free)} mutually free windows")

    free_serialized = [
        {"start": s.isoformat(), "end": e.isoformat()}
        for s, e in free
    ]

    return {
        **state,
        "free_slots": free_serialized,
        "unauthenticated_participants": unauthenticated
    }


def draft_reply(state: AccordState) -> AccordState:
    print("\nDrafting reply...")
    slots = state["free_slots"][:3]
    slot_text = "\n".join([
        f"- Option {i+1}: {s['start']} to {s['end']}"
        for i, s in enumerate(slots)
    ])

    participant_count = len(state["participants"])
    unauthenticated = state.get("unauthenticated_participants", [])

    caveat = ""
    if unauthenticated:
        caveat = f"""
Note: The calendars for {', '.join(unauthenticated)} could not be directly checked.
The proposed times are based on the available calendars. Mention this politely
and ask those participants to confirm availability.
"""

    prompt = f"""
You are Accord, an AI scheduling assistant coordinating a meeting across
{participant_count} participants. Write a short, professional email
proposing meeting times that work for everyone based on their combined availability.

Original request: "{state['raw_request']}"
Participants: {state['participants']}

Available slots (mutually free for all checked calendars):
{slot_text}
{caveat}
Keep it concise, friendly, and professional.
End with asking them to confirm which time works.
Do not include subject line - just the email body.
"""
    response = llm.invoke(prompt)
    print("   Draft ready to review:")
    content = response.content
    if isinstance(content, list):
        content = content[0]["text"] if isinstance(content[0], dict) else content[0]
    return {**state, "draft_reply": content}


def relax_constraints(state: AccordState) -> AccordState:
    print(f"\nNo slots found. Relaxing constraints (attempt {state['retry_count'] + 1})...")
    return {**state, "retry_count": state["retry_count"] + 1}


def negotiate(state: AccordState) -> AccordState:
    print("\nNegotiating compromise...")
    prompt = f"""
You are Accord, a scheduling assistant. You tried to find a meeting slot
but could not find one that satisfies all constraints.

Original request: "{state['raw_request']}"
Participants: {state['participants']}
Attempts made: {state['retry_count']}

Write a short, professional email that:
1. Acknowledges you couldn't find a perfect slot
2. Explains the constraint causing the conflict
3. Proposes a specific compromise
4. Asks them to confirm or suggest alternatives

Be honest, professional and solution-focused. No subject line, just body.
"""
    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = content[0]["text"] if isinstance(content[0], dict) else content[0]
    return {**state, "draft_reply": content, "is_compromise": True}


def should_draft_or_retry(state: AccordState) -> str:
    if state["free_slots"]:
        return "draft"
    elif state["retry_count"] < 2:
        return "relax"
    else:
        return "negotiate"


def build_accord_graph():
    graph = StateGraph(AccordState)

    graph.add_node("parse", parse_request)
    graph.add_node("fetch", fetch_availability)
    graph.add_node("draft", draft_reply)
    graph.add_node("relax", relax_constraints)
    graph.add_node("negotiate", negotiate)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "fetch")
    graph.add_conditional_edges("fetch", should_draft_or_retry, {
        "draft": "draft",
        "relax": "relax",
        "negotiate": "negotiate"
    })
    graph.add_edge("relax", "fetch")
    graph.add_edge("negotiate", END)
    graph.add_edge("draft", END)

    return graph.compile()


if __name__ == "__main__":
    accord = build_accord_graph()

    test_request = """
    Hi, could we set up a 30 minute call sometime in the next 5 days?
    It'll be with vanshika.m.jagtap@gmail.com. Morning works best, EST timezone.
    """

    print("=" * 50)
    print("Incoming request:")
    print(test_request)
    print("=" * 50)

    result = accord.invoke({
        "raw_request": test_request,
        "participants": [],
        "duration_mins": 30,
        "timeframe_days": 5,
        "timezone": "UTC",
        "preferred_time": "any",
        "excluded_days": [],
        "free_slots": [],
        "draft_reply": "",
        "retry_count": 0,
        "is_compromise": False,
        "unauthenticated_participants": []
    })

    print("\n" + "=" * 50)
    print("DRAFT REPLY:")
    print("=" * 50)
    print(result["draft_reply"])