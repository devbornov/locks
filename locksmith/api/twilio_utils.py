# twilio_utils.py
from twilio.rest import Client
import os

def send_sms_to_locksmith(to_number, message):
    client = Client(os.getenv("ACb9993d68e0c490eb54de4f61018d5691"), os.getenv("6e7b89c3e473c1a92a9d31e6868fee66"))
    client.messages.create(
        to=to_number,
        from_=os.getenv("+12185229562"),
        body=message
    )
