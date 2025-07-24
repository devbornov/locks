# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from datetime import datetime
from datetime import time
from .models import Booking
from .twilio_utils import send_sms_to_locksmith
import pytz

def notify_locksmiths():
    print("🔔 Starting notify_locksmiths task...")
    today = timezone.localtime(timezone.now()).date()
    print(f"📅 Today's date: {today}")

    bookings = Booking.objects.filter(scheduled_date__date=today, status='Scheduled')
    print(f"🔍 Found {bookings.count()} scheduled bookings for today.")

    for booking in bookings:
        locksmith_service = getattr(booking, 'locksmith_service', None)
        locksmith = getattr(locksmith_service, 'locksmith', None)

        print(f"📦 Booking ID: {booking.id}, Customer: {booking.customer_name}, Scheduled at: {booking.scheduled_date}")

        if locksmith:
            print(f"🔑 Locksmith ID: {locksmith.id}, Phone: {locksmith.phone_number}")
            if locksmith.phone_number:
                msg = f"Hi, you have a booking today at {booking.scheduled_date.strftime('%I:%M %p')} for {booking.customer_name}."
                try:
                    send_sms_to_locksmith(locksmith.phone_number, msg)
                    print("✅ SMS sent successfully.")
                except Exception as e:
                    print(f"❌ Failed to send SMS: {e}")
            else:
                print("⚠️ Locksmith has no phone number.")
        else:
            print("⚠️ No locksmith assigned to this booking.")

def start():
    print("⏱️ Starting scheduler...")
    scheduler = BackgroundScheduler(timezone=pytz.timezone("Australia/Sydney"))
    scheduler.add_job(notify_locksmiths, 'cron', hour=8, minute=0)
    scheduler.start()
    print("🚀 Scheduler started and job registered for 8:00 AM daily.")