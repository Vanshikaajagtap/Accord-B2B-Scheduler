 # Accord — Agentic B2B Meeting Scheduler

> AI that eliminates scheduling ping-pong by autonomously finding meeting times, drafting replies, and booking calendar events — with a human-in-the-loop approval step before anything is sent.

---

## 🎥 Demo

https://www.loom.com/share/353ae527950449bcbffccf3de60e3512

---

##  Track

**Agentic AI & Workforce Augmentation**

---

## The Problem

Scheduling a meeting between multiple stakeholders across time zones is a massive time sink. High-value workers waste hours on "email ping-pong" — manually cross-referencing calendars, converting time zones, and drafting back-and-forth replies before a slot is ever agreed on.

Existing tools like Calendly just shift the burden onto the client. They can't handle natural language constraints like *"morning EST, no Fridays"* and they don't coordinate across multiple internal participants.

---

## The Solution

Accord is an autonomous scheduling agent embedded in your workflow. It:

1. **Reads** a natural language meeting request (email or Slack)
2. **Parses** intent, participants, duration, timezone and constraints using an LLM
3. **Fetches** real-time availability from all participants via Google Calendar API
4. **Finds** overlapping free windows across everyone's calendars
5. **Drafts** a professional reply proposing the best time slots
6. **Waits** for human approval before sending anything (HITL gateway)
7. **Sends** the approved email via Gmail and **books** the Google Calendar event with a Meet link

---

## The Pipeline

```
Incoming Request
      ↓
  LLM Parse (Gemini)
      ↓
  Fetch Calendars (Google Calendar API)
      ↓
  Intersection Engine (find overlapping free slots)
      ↓
  Slot found? ──No──→ Relax constraints → retry
      ↓ Yes
  Draft Reply (Gemini)
      ↓
  HITL Gateway (human approves)
      ↓
  Send Email (Gmail API) + Book Event (Calendar API)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Orchestration | LangGraph |
| LLM | Gemini 3.0 Flash |
| Core Language | Python |
| Calendar Integration | Google Calendar API |
| Email Integration | Gmail API |
| Auth | OAuth 2.0 |
| UI | Streamlit |

---

## Running Locally

### Prerequisites
- Python 3.11+
- A Google Cloud Project with Gmail API and Google Calendar API enabled
- OAuth 2.0 Desktop App credentials (`credentials.json`)
- Gemini API key

### Setup

```bash
# Clone the repo
git clone https://github.com/Vanshikaajagtap/Accord-B2B-Scheduler.git
cd Accord-B2B/accord

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install langgraph langchain-google-genai google-auth-oauthlib \
    google-auth-httplib2 google-api-python-client streamlit pytz \
    python-dotenv
```

### Configure environment

Create a `.env` file inside the `accord` folder:
```
GOOGLE_API_KEY=your_gemini_api_key_here
```

Place your `credentials.json` (from GCP) inside the `accord` folder.

### Authenticate

```bash
python auth_test.py
```

This opens a browser tab to authorize Google access. After approval, a `token.json` is saved locally.

### Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Project Structure

```
accord/
  agent.py          # LangGraph agent — nodes, state, graph
  app.py            # Streamlit UI + HITL gateway
  auth_test.py      # Google OAuth flow
  calendar_tool.py  # Free/busy fetch + event creation
  gmail_tool.py     # Email sending
  credentials.json  # GCP OAuth credentials (not committed)
  token.json        # Auth token (not committed)
  .env              # API keys (not committed)
```

---

##  Team

### Innoventurers
 
| Vanshika Jagtap | vanshika.m.jagtap@gmail.com |
| Ipsita Roy | ipshitaroy2007@gmail.com |
| Fathima Ummerchintavida | fathimafalaq.em@gmail.com |
| Roshini R | rr8415@srmist.edu.in |
