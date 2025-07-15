# locksmith/email_utils.py

import logging
import threading
from django.core.mail import EmailMessage
from django.contrib.auth import get_user_model
from api.utils import is_valid_email

logger = logging.getLogger(__name__)
User = get_user_model()

def send_bulk_locksmith_emails(subject, body, exclude_user_id=None):
    def _send():
        all_locksmiths = User.objects.filter(role='locksmith')
        if exclude_user_id:
            all_locksmiths = all_locksmiths.exclude(id=exclude_user_id)

        bcc_list = [user.email for user in all_locksmiths if user.email and is_valid_email(user.email)]

        logger.info(f"[EMAIL DEBUG] Total valid locksmith emails to notify: {len(bcc_list)}")

        chunk_size = 10
        for i in range(0, len(bcc_list), chunk_size):
            chunk = bcc_list[i:i + chunk_size]
            try:
                email = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email="contact@lockquick.com.au",
                    to=["contact@lockquick.com.au"],  # visible field
                    bcc=chunk
                )
                email.send(fail_silently=False)
                logger.info(f"[EMAIL] Sent to chunk: {chunk}")
            except Exception as e:
                logger.error(f"[EMAIL ERROR] Failed sending chunk: {e}")

    threading.Thread(target=_send).start()
