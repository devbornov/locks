from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, LocksmithViewSet, CarKeyDetailsViewSet, 
    ServiceViewSet, TransactionViewSet, 
    ServiceRequestViewSet, ServiceBidViewSet, 
    AdminSettingsViewSet,AllLocksmiths,CustomersViewSet
)

# Initialize Default Router
router = DefaultRouter()
router.register(r'users', UserViewSet),
router.register(r'locksmiths', LocksmithViewSet)
router.register(r'alllocksmiths', AllLocksmiths,basename='alllocksmiths'),
router.register(r'allcustomers', CustomersViewSet,basename='allcustomers'),
router.register(r'carkeydetails', CarKeyDetailsViewSet)
router.register(r'services', ServiceViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'servicerequests', ServiceRequestViewSet)  # Add ServiceRequest viewset
router.register(r'servicebids', ServiceBidViewSet)  # Add ServiceBid viewset
router.register(r'adminsettings', AdminSettingsViewSet)  # Add AdminSettings viewset

# URL patterns
urlpatterns = [
    path('', include(router.urls)),
]
