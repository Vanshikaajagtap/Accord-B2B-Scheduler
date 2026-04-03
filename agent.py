from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import TypedDict, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
from auth_test import get_credentials
from calendar_tool import get_calendar_service, get_free_busy, find_free_slots
from gmail_tool import get_gmail_service, create_draft

load_dotenv()
 
class AccordState(TypedDict):
    raw_request: str          
    participants: List[str]   
    duration_mins: int         
    timeframe_days: int        
    timezone: str              
    free_slots: List[dict]    
    draft_reply: str           
    retry_count: int          

llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)


def parse_request(state: AccordState) -> AccordState:
    #Node 1 : LLM extracts structured info from raw request
    print("\nParsing request...")

    prompt = f"""
You are a scheduling assistant. Extract info from this meeting request.
Return ONLY valid JSON, no explanation, no markdown.

Request: "{state['raw_request']}"

Return this exact structure:
{{
  "participants": ["email1@example.com"],
  "duration_mins": 30,
  "timeframe_days": 7,
  "timezone": "UTC"
}}

Rules:
- participants: list of email addresses mentioned. If none, return []
- duration_mins: integer. Default 30 if not mentioned.
- timeframe_days: how many days ahead to search. "next week" = 7, "today" = 1. Default 5.
- timezone: best guess from context. Default "UTC"
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
    }


def fetch_availability(state: AccordState) -> AccordState:
    #Node 2 : hit Google Calendar API for all participants
    print("\nFetching availability...")

    creds = get_credentials()
    service = get_calendar_service(creds)

    # Expand search window if retrying
    days = state["timeframe_days"] + (state["retry_count"] * 3)

    now = datetime.utcnow().isoformat() + "Z"
    future = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"

    busy = get_free_busy(service, state["participants"], now, future, state["timezone"])
    free = find_free_slots(busy, now, future, state["duration_mins"], state["timezone"])

    print(f"   Found {len(free)} free windows")
 
    free_serialized = [
        {"start": s.isoformat(), "end": e.isoformat()}
        for s, e in free
    ]

    return {**state, "free_slots": free_serialized}


def draft_reply(state: AccordState) -> AccordState:
    #Node 3 : LLM writes a professional reply proposing times.
    print("\nDrafting reply...")

    slots = state["free_slots"][:3]  
    slot_text = "\n".join([
        f"- Option {i+1}: {s['start']} to {s['end']}"
        for i, s in enumerate(slots)
    ])

    prompt = f"""
You are Accord, an AI scheduling assistant. Write a short, professional email 
proposing meeting times based on this request and available slots.

Original request: "{state['raw_request']}"

Available slots:
{slot_text}

Keep it concise, friendly, and professional. 
End with asking them to confirm which time works.
Do not include subject line — just the email body.
"""

    response = llm.invoke(prompt)
    print("   Draft ready to review:")

    content = response.content
    if isinstance(content, list):
        content = content[0]["text"] if isinstance(content[0], dict) else content[0]
    return {**state, "draft_reply": content}


def relax_constraints(state: AccordState) -> AccordState:
    #Node 4 : no slots found, widen the search window.
    print(f"\nNo slots found. Relaxing constraints (attempt {state['retry_count'] + 1})...")
    return {**state, "retry_count": state["retry_count"] + 1}


def should_draft_or_retry(state: AccordState) -> str:
    if state["free_slots"]:
        return "draft"
    elif state["retry_count"] < 3:
        return "relax"
    else:
        return "draft"  



def build_accord_graph():
    graph = StateGraph(AccordState)

    graph.add_node("parse", parse_request)
    graph.add_node("fetch", fetch_availability)
    graph.add_node("draft", draft_reply)
    graph.add_node("relax", relax_constraints)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "fetch")
    graph.add_conditional_edges("fetch", should_draft_or_retry, {
        "draft": "draft",
        "relax": "relax"
    })
    graph.add_edge("relax", "fetch")  
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
        "free_slots": [],
        "draft_reply": "",
        "retry_count": 0
    })

    print("\n" + "=" * 50)
    print("DRAFT REPLY:")
    print("=" * 50)
    print(result["draft_reply"])