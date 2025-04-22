import json
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.utils.encoding import force_str

User = get_user_model()

class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def extract_role_from_body(self, request):
        try:
            body_unicode = force_str(request.body)
            body_data = json.loads(body_unicode)
            role = body_data.get('role', 'customer')
            return role if role in ['locksmith', 'customer'] else 'customer'
        except Exception:
            return 'customer'

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        # Auto-generate unique username
        email = data.get("email", "")
        base_username = slugify(email.split("@")[0])
        unique_username = base_username
        counter = 1
        while User.objects.filter(username=unique_username).exists():
            unique_username = f"{base_username}{counter}"
            counter += 1
        user.username = unique_username

        # Assign role
        role = self.extract_role_from_body(request)
        user.role = role

        return user

    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            user = sociallogin.user
            role = self.extract_role_from_body(request)
            user.role = role
            user.save()
        return super().pre_social_login(request, sociallogin)
   