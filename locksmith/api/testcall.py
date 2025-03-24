from twilio.rest import Client

# Twilio Credentials (Replace with actual credentials)
TWILIO_ACCOUNT_SID = "ACba1e3f20eb7083c73471a9e87c04802c"  
TWILIO_AUTH_TOKEN = "ca2a6daa04eed144e8bb9af1269a265e"  
TWILIO_PHONE_NUMBER = "+12233572123" 

def call_locksmith(locksmith_phone, locksmith_name, booking_id):
    """Function to call the locksmith."""
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    message = f"Hello {locksmith_name}, you have a new booking. Booking ID: {booking_id}."
    
    call = client.calls.create(
        twiml=f'<Response><Say>{message}</Say></Response>',
        to=locksmith_phone,
        from_=TWILIO_PHONE_NUMBER
    )
    
    print(f"📞 Call triggered to {locksmith_name} ({locksmith_phone}) - Call SID: {call.sid}")
    return call.sid

# 🔹 Test the call function
test_phone = "+917356157590"  # Replace with your test phone number
test_name = "John Doe"
test_booking_id = 101

call_locksmith(test_phone, test_name, test_booking_id)