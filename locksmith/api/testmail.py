from django.core.mail import send_mail

send_mail(
    'Test Subject',
    'This is a test email.',
    'contact@lockquick.com.au',
    ['swedeninsights@gmail.com'],
    fail_silently=False,
)
