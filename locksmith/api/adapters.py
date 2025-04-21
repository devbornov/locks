from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.utils.text import slugify
from django.contrib.auth import get_user_model

User = get_user_model()

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        
        # Auto-generate username from email
        email = data.get("email", "")
        base_username = slugify(email.split("@")[0])
        unique_username = base_username
        counter = 1

        while User.objects.filter(username=unique_username).exists():
            counter += 1
            unique_username = f"{base_username}{counter}"

        user.username = unique_username
        return user
