from allauth.account.signals import user_logged_in
from django.dispatch import receiver
from .models import Customer, Locksmith

@receiver(user_logged_in)
def assign_user_role(request, user, **kwargs):
    if not user.role:  # Only if not already set
        user.role = "customer"  # or detect logic
        user.save()
        Customer.objects.get_or_create(user=user)
