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
from api.views import CreateAdminUserView, UserRegisterView, LocksmithRegisterView, LoginView,LocksmithProfileView , LogoutView

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
    path("logout/", LogoutView.as_view(), name="logout"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)