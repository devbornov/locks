# from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
# from .models import User



# class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
#     def pre_social_login(self, request, sociallogin):
#         """
#         Assign a role based on the login page the user came from.
#         """
#         user = sociallogin.user
#         role_from_request = request.GET.get("role")  # Get role from URL parameter

#         if not user.email:
#             return  # Ignore if email is missing
        
#         try:
#             # If user exists, connect to existing account
#             existing_user = User.objects.get(email=user.email)
#             sociallogin.connect(request, existing_user)
#         except User.DoesNotExist:
#             # Assign role based on which page they logged in from
#             if role_from_request in ["locksmith", "customer"]:
#                 user.role = role_from_request
#             else:
#                 user.role = "customer"  # Default role if role is missing
#             user.save()
