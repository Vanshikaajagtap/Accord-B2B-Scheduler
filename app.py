import streamlit as st
from agent import build_accord_graph
from auth_test import (get_credentials, authenticate_email,
                       list_authenticated_emails, is_email_authenticated)
from gmail_tool import get_gmail_service, send_email

st.set_page_config(page_title="Accord", layout="wide")
st.title("Accord : Agentic B2B Meeting Scheduler")

if "result" not in st.session_state:
    st.session_state.result = None
if "client_email" not in st.session_state:
    st.session_state.client_email = ""
if "auth_message" not in st.session_state:
    st.session_state.auth_message = None

with st.sidebar:
    st.header("Participant Authentication")
    st.caption("Each participant must authenticate once so Accord can check their calendar.")

    authenticated = list_authenticated_emails()
    if authenticated:
        st.write("Authenticated accounts:")
        for email in authenticated:
            st.success(email)
    else:
        st.info("No participants authenticated yet.")

    st.divider()
    new_email = st.text_input("Add participant email:")
    if st.button("Authenticate", type="primary"):
        if new_email:
            try:
                authenticate_email(new_email)
                st.session_state.auth_message = f"Authenticated {new_email}"
                st.rerun()
            except Exception as e:
                st.error(f"Authentication failed: {e}")

    if st.session_state.auth_message:
        st.success(st.session_state.auth_message)
        st.session_state.auth_message = None

col1, col2 = st.columns(2)
with col1:
    request = st.text_area("Incoming scheduling request:", height=150,
        value="Hi, could we set up a 30 minute call in the next 5 days? "
              "Morning EST works best. Participants: vanshika.m.jagtap@gmail.com")
with col2:
    client_email = st.text_input("Reply-to email:", value="vanshika.m.jagtap@gmail.com")
    run = st.button("Run Accord", type="primary")

if run:
    with st.spinner("Accord is checking all participant calendars..."):
        accord = build_accord_graph()
        result = accord.invoke({
            "raw_request": request,
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
        st.session_state.result = result
        st.session_state.client_email = client_email
    st.success("Draft ready!")

if st.session_state.result:
    result = st.session_state.result

    st.divider()
    st.subheader("Participants Checked")

    participants = result.get("participants", [])
    unauthenticated = result.get("unauthenticated_participants", [])

    for email in participants:
        if email in unauthenticated:
            st.warning(f"{email} - calendar not directly accessible (fallback query used)")
        else:
            st.success(f"{email} - calendar checked with their own credentials")

    st.divider()
    st.subheader("Draft Reply")
    st.info(result["draft_reply"])

    st.divider()
    st.subheader("Human-in-the-Loop Gateway")
    st.warning("Accord will not send anything until YOU approve.")

    approve_col, reject_col = st.columns(2)

    with approve_col:
        if st.button("Approve & Send", type="primary", use_container_width=True, key="approve_btn"):
            try:
                creds = get_credentials()
                gmail = get_gmail_service(creds)
                r = send_email(
                    gmail,
                    to=st.session_state.client_email,
                    subject="Meeting Request - Available Times",
                    body=result["draft_reply"]
                )
                st.success(f"Email sent! ID: {r['id']}")
            except Exception as e:
                st.error(f"Email failed: {e}")

            try:
                from calendar_tool import get_calendar_service, create_calendar_event
                creds = get_credentials()
                cal = get_calendar_service(creds)
                first_slot = result["free_slots"][0]
                event = create_calendar_event(
                    cal,
                    summary="Meeting via Accord",
                    attendees=result["participants"] + [st.session_state.client_email],
                    start_time=first_slot["start"],
                    end_time=first_slot["end"],
                    timezone=result["timezone"]
                )
                st.success("Calendar event created!")
            except Exception as e:
                st.error(f"Calendar failed: {e}")

    with reject_col:
        if st.button("Reject & Discard", use_container_width=True, key="reject_btn"):
            st.session_state.result = None
            st.rerun()