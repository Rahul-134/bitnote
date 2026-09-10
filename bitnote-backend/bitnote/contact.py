import os

import requests
from fastapi import APIRouter, HTTPException
from bitnote.schemas.contact_schema import ContactRequest

router = APIRouter()

# Raw SMTP (port 25/465/587) is blocked outbound on Render's free tier (and
# many other free-tier platforms), so this sends via Resend's HTTPS API
# instead — works identically in local dev and in production.
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
CONTACT_TO_EMAIL = os.getenv("CONTACT_TO_EMAIL")
# Resend's shared sandbox sender — works without owning/verifying a domain,
# as long as CONTACT_TO_EMAIL is the same address the Resend account was
# created with. Point this at a verified domain address once you have one.
CONTACT_FROM_EMAIL = os.getenv("CONTACT_FROM_EMAIL", "onboarding@resend.dev")


@router.post("/")
def send_contact_email(data: ContactRequest):

    if not RESEND_API_KEY or not CONTACT_TO_EMAIL:
        raise HTTPException(
            status_code=500,
            detail="Contact form is not configured. Set RESEND_API_KEY and "
            "CONTACT_TO_EMAIL (see .env.example).",
        )

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from": CONTACT_FROM_EMAIL,
                "to": [CONTACT_TO_EMAIL],
                "reply_to": data.email,
                "subject": f"New Contact from {data.name}",
                "text": f"Name: {data.name}\nEmail: {data.email}\n\nMessage:\n{data.message}",
            },
            timeout=15,
        )
        response.raise_for_status()

        return {"success": True, "message": "Email sent successfully"}

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {e}")
