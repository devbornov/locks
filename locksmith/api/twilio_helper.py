from twilio.rest import Client
from django.conf import settings

def make_twilio_call(to_phone, message):
    """Make an automated voice call using Twilio."""
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    call = client.calls.create(
        to=to_phone,
        from_=settings.TWILIO_PHONE_NUMBER,
        twiml=f'<Response><Say>{message}</Say></Response>'
    )

    return call.sid
