# # from twilio.rest import Client

# # # Twilio Credentials (Replace with actual credentials)
# # TWILIO_ACCOUNT_SID = "ACba1e3f20eb7083c73471a9e87c04802c"  
# # TWILIO_AUTH_TOKEN = "ca2a6daa04eed144e8bb9af1269a265e"  
# # TWILIO_PHONE_NUMBER = "+12233572123" 

# # def call_locksmith(locksmith_phone, locksmith_name, booking_id):
# #     """Function to call the locksmith."""
# #     client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
# #     message = f"Hello {locksmith_name}, you have a new booking. Booking ID: {booking_id}."
    
# #     call = client.calls.create(
# #         twiml=f'<Response><Say>{message}</Say></Response>',
# #         to=locksmith_phone,
# #         from_=TWILIO_PHONE_NUMBER
# #     )
    
# #     print(f"📞 Call triggered to {locksmith_name} ({locksmith_phone}) - Call SID: {call.sid}")
# #     return call.sid

# # # 🔹 Test the call function
# # test_phone = "+917356157590"  # Replace with your test phone number
# # test_name = "John Doe"
# # test_booking_id = 101

# # call_locksmith(test_phone, test_name, test_booking_id)


# # from twilio.rest import Client

# # # Twilio credentials (Replace with your real ones)
# # account_sid = 'ACb9993d68e0c490eb54de4f61018d5691'
# # auth_token = '6e7b89c3e473c1a92a9d31e6868fee66'

# # client = Client(account_sid, auth_token)

# # messages = client.messages.list(limit=50)
# # target_booking_id = '626'

# # for msg in messages:
# #     if f"booking (ID: {target_booking_id})" in msg.body:
# #         print("📬 Match Found!")
# #         print("SID:", msg.sid)
# #         print("To:", msg.to)
# #         print("From:", msg.from_)
# #         print("Status:", msg.status)
# #         print("Date Sent:", msg.date_sent)
# #         print("Body:\n", msg.body)
# #         break
# # else:
# #     print("❌ No message found for booking ID:", target_booking_id)





# # from twilio.rest import Client


# # account_sid = 'ACb9993d68e0c490eb54de4f61018d5691'
# # auth_token = '6e7b89c3e473c1a92a9d31e6868fee66'
# # client = Client(account_sid, auth_token)

# # to_number = '+61414952925'
# # target_phrase = "booking (ID: 626)"

# # messages = client.messages.list(to=to_number, limit=100)

# # matches = []
# # for msg in messages:
# #     if target_phrase in msg.body:
# #         matches.append(msg)

# # # Show duplicates if more than 1
# # if len(matches) > 1:
# #     print(f"⚠️ {len(matches)} duplicate messages found:")
# #     for m in matches:
# #         print(f"SID: {m.sid}, Sent at: {m.date_sent}, Body: {m.body.strip()[:60]}...")
# # else:
# #     print("✅ No duplicates found.")



# from twilio.rest import Client

# # Twilio credentials
# account_sid = 'ACb9993d68e0c490eb54de4f61018d5691'
# auth_token = '6e7b89c3e473c1a92a9d31e6868fee66'
# client = Client(account_sid, auth_token)

# # Set target phone number and phrase to search
# to_number = '+61414952925'
# target_phrase = "booking (ID: 626)"

# # Fetch last 100 messages sent to that number
# messages = client.messages.list(to=to_number, limit=100)

# matches = []
# for msg in messages:
#     if target_phrase in msg.body:
#         matches.append(msg)

# # Print full details
# if len(matches) > 0:
#     print(f"⚠️ {len(matches)} message(s) found:")
#     for m in matches:
#         print("-------------------------------------------------")
#         print(f"SID       : {m.sid}")
#         print(f"To        : {m.to}")
#         print(f"From      : {m.from_}")
#         print(f"Status    : {m.status}")
#         print(f"Sent At   : {m.date_sent}")
#         print("Body:")
#         print(m.body)
# else:
#     print("✅ No messages found containing that phrase.")
