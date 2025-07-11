# from django.core.mail import send_mail
# import random
# from django.utils import timezone

# def send_email_otp(user):
#     otp = str(random.randint(100000, 999999))
#     user.otp_code = otp
#     user.otp_expiry = timezone.now() + timezone.timedelta(minutes=5)
#     user.save()
#     send_mail(
#         subject="Your Login OTP",
#         message=f"Your OTP is {otp}. It expires in 5 minutes.",
#         from_email="contact@lockquick.com.au",
#         recipient_list=[user.email],
#     )




from django.core.mail import send_mail
from django.utils import timezone
import random

def send_email_otp(user):
    otp = str(random.randint(100000, 999999))
    user.otp_code = otp
    user.otp_expiry = timezone.now() + timezone.timedelta(minutes=5)
    user.save()

    subject = "Your LockQuick OTP"
    message = (
        f"Hello {user.username},\n\n"
        f"Your One-Time Password (OTP) is: {otp}\n"
        f"This OTP will expire in 5 minutes.\n\n"
        f"If you did not request this, please ignore this email.\n\n"
        f"— LockQuick Team"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email="contact@lockquick.com.au",
        recipient_list=[user.email],
        fail_silently=False
    )




import pyotp
from django.utils import timezone

def verify_user_otp(user, otp_code):
    # ✅ Try TOTP first
    if user.totp_secret:
        totp = pyotp.TOTP(user.totp_secret)
        if totp.verify(otp_code, valid_window=1):
            return True, "totp"

    # ✅ If TOTP fails, try Email OTP
    if user.otp_code and user.otp_expiry:
        if timezone.now() > user.otp_expiry:
            return False, "expired"
        if otp_code == user.otp_code:
            # Invalidate OTP
            user.otp_code = None
            user.otp_expiry = None
            user.save()
            return True, "email"

    return False, "invalid"



def send_password_reset_otp(user):
    otp = str(random.randint(100000, 999999))
    user.otp_code = otp
    user.otp_expiry = timezone.now() + timezone.timedelta(minutes=10)
    user.save()

    subject = "Password Reset OTP - LockQuick"
    message = f"Your OTP for password reset is {otp}. It expires in 10 minutes."

    send_mail(
        subject=subject,
        message=message,
        from_email="contact@lockquick.com.au",
        recipient_list=[user.email],
        fail_silently=False
    )
    
    
    
    
    
    
    
    
    
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

# Add any domains you want to block
BLOCKED_DOMAINS = ['example.com', 'tempmail.com', 'mailinator.com', 'kimdyn.com']

def is_valid_email(email):
    """
    Validate email format and exclude known disposable domains.
    """
    try:
        validate_email(email)
        domain = email.split('@')[-1].lower()
        if domain in BLOCKED_DOMAINS:
            return False
        return True
    except ValidationError:
        return False
