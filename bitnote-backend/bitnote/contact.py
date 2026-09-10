import os

from fastapi import APIRouter, HTTPException
from bitnote.schemas.contact_schema import ContactRequest
import aiosmtplib
from email.message import EmailMessage

router = APIRouter()

EMAIL_USER = os.getenv("CONTACT_EMAIL_USER")
EMAIL_PASS = os.getenv("CONTACT_EMAIL_PASS")  # Gmail App Password, no spaces


@router.post("/")
async def send_contact_email(data: ContactRequest):

    if not EMAIL_USER or not EMAIL_PASS:
        raise HTTPException(
            status_code=500,
            detail="Contact form is not configured. Set CONTACT_EMAIL_USER and "
            "CONTACT_EMAIL_PASS (see .env.example).",
        )

    try:
        message = EmailMessage()
        message["From"] = EMAIL_USER
        message["To"] = EMAIL_USER
        message["Subject"] = f"New Contact from {data.name}"

        message.set_content(f"""
Name: {data.name}
Email: {data.email}

Message:
{data.message}
        """)

        await aiosmtplib.send(
            message,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=EMAIL_USER,
            password=EMAIL_PASS,
        )

        return {"success": True, "message": "Email sent successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))