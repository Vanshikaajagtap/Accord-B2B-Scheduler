import streamlit as st
from agent import build_accord_graph
from auth_test import get_credentials
from gmail_tool import get_gmail_service, send_email

st.set_page_config(page_title="Accord", layout="wide")

st.title("Accord : Agentic B2B Meeting  Scheduler")
st.caption("AI that handles complex scheduling so you don't have to.")
 
col1, col2 = st.columns(2)

with col1:
    st.subheader("Incoming Request")
    request = st.text_area(
        "Paste the scheduling request here:",
        value="Hi, could we set up a 30 minute call sometime in the next 5 days? Morning works best, EST timezone. My email is vanshika.m.jagtap@gmail.com",
        height=150
    )
    client_email = st.text_input("Client's email (to send reply to):", value="vanshika.m.jagtap@gmail.com")
    run = st.button("Run Accord", type="primary", use_container_width=True)

with col2:
    st.subheader("Agent Reasoning Log")
    log_box = st.empty()
 
if run:
    logs = []

    def log(msg):
        logs.append(msg)
        log_box.markdown("\n\n".join(logs))

    with st.spinner("Accord is working..."):
        log("**Step 1:** Parsing request with Gemini...")
        
        accord = build_accord_graph()
        result = accord.invoke({
            "raw_request": request,
            "participants": [],
            "duration_mins": 30,
            "timeframe_days": 5,
            "timezone": "UTC",
            "free_slots": [],
            "draft_reply": "",
            "retry_count": 0
        })

        log(f"**Parsed:** {result['participants']} · {result['duration_mins']} mins · {result['timeframe_days']} days")
        log(f"**Step 2:** Fetched calendars for {len(result['participants'])} participant(s)")
        log(f"**Found:** {len(result['free_slots'])} overlapping free window(s)")
        log("**Step 3:** Drafted professional reply")
        log("**Step 4:** Waiting for your approval...")
 
    st.divider()
    st.subheader("Draft Reply")
    st.info(result["draft_reply"])
 
    st.divider()
    st.subheader("Human-in-the-Loop Gateway")
    st.warning("Accord will not send anything until YOU approve.")

    approve_col, reject_col = st.columns(2)

    with approve_col:
        if st.button("Approve & Send", type="primary", use_container_width=True):
            creds = get_credentials()
            gmail = get_gmail_service(creds)
            send_email(
                gmail,
                to=client_email,
                subject="Meeting Request — Available Times",
                body=result["draft_reply"]
            )
            st.success("Email sent! Calendar invite will follow once client confirms.")

    with reject_col:
        if st.button("Reject & Discard", use_container_width=True):
            st.error("Draft discarded. Run Accord again with a different request.")