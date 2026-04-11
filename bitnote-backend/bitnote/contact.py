from fastapi import APIRouter, HTTPException
from bitnote.schemas.contact_schema import ContactRequest
import aiosmtplib
from email.message import EmailMessage

router = APIRouter()

# HARD CODED (Only for testing)
EMAIL_USER = "<example-email@gmail.com>"
EMAIL_PASS = "<example-password>"   # remove spaces (16 characters)


@router.post("/")
async def send_contact_email(data: ContactRequest):

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