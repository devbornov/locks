"""
URL configuration for locksmith project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path , include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from api.views import CreateAdminUserView, UserRegisterView, LocksmithRegisterView, LoginView,LocksmithProfileView , LogoutView  , get_mcc_code ,CustomFacebookLogin,CustomGoogleLogin
from api.views import stripe_webhook
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from api.views import GoogleLoginAPI



class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter

class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # Get JWT token
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  
    path('create-admin/', CreateAdminUserView.as_view(), name='create-admin'),# Refresh JWT token
    path('register/user/', UserRegisterView.as_view(), name='register-user'),
    path('register/locksmith/', LocksmithRegisterView.as_view(), name='register-locksmith'),
    path('locksmith/profile/update/', LocksmithProfileView.as_view(), name='locksmith-profile-update'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path("stripe-webhook/", stripe_webhook, name="stripe-webhook"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("get-mcc/", get_mcc_code, name="get_mcc"),
    # path("auth/social/", include("allauth.socialaccount.urls")),
    # path("update-mcc/", update_mcc, name="update_mcc"),
    


    path('accounts/', include('allauth.urls')),
    path('accounts/', include('allauth.urls')),  # Optional for browser login
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/registration/', include('dj_rest_auth.registration.urls')),
    path('auth/social/', include('allauth.socialaccount.urls')), 
    path('auth/google/', GoogleLoginAPI.as_view(), name='google_login_api'),# Only if needed
    path('api/auth/google/', CustomGoogleLogin.as_view(), name='google_login'),
    path('api/auth/facebook/', CustomFacebookLogin.as_view(), name='facebook_login'),
    # path('facebook-data-deletion/', facebook_data_deletion, name='facebook_data_deletion'),


    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)