import base64
from email.message import EmailMessage
from googleapiclient.discovery import build

def get_gmail_service(creds):
    return build("gmail", "v1", credentials=creds)

def send_email(service, to, subject, body):
    
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(
        userId="me",
        body={"raw": encoded}
    ).execute()
    print(f"Email sent, Message ID: {result['id']}")
    return result

def create_draft(service, to, subject, body):
     
    
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": encoded}}
    ).execute()
    print(f"Draft saved! Draft ID: {draft['id']}")
    return draft

#test code

if __name__ == "__main__":
    from auth_test import get_credentials

    creds = get_credentials()
    service = get_gmail_service(creds)
 
    send_email(
        service,
        to="vanshika.m.jagtap@gmail.com",   
        subject="Accord Test Email",
        body="If you're reading this, Gmail integration is working!"
    )