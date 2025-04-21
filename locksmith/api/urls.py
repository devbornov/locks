from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, LocksmithViewSet, CarKeyDetailsViewSet, 
    ServiceViewSet, TransactionViewSet, 
    ServiceRequestViewSet, ServiceBidViewSet, 
    AdminSettingsViewSet,AllLocksmiths,CustomersViewSet,AdmincomissionViewSet,CustomerServiceRequestViewSet,Approvalverification, BookingViewSet , 
    AdminLocksmithServiceViewSet,AdminLocksmithServiceApprovalViewSet , CustomerProfileViewSet , ContactMessageViewSet , ForgotPasswordViewSet
)
from api.views import GoogleLoginAPI





# Initialize Default Router
router = DefaultRouter()
router.register(r'users', UserViewSet),
router.register(r'locksmiths', LocksmithViewSet)
router.register(r'Approvalverification',Approvalverification,basename='Approvalverification')
router.register(r'alllocksmiths', AllLocksmiths,basename='alllocksmiths')
router.register(r'allcustomers', CustomersViewSet,basename='allcustomers')
router.register(r'carkeydetails', CarKeyDetailsViewSet)
router.register(r'services', ServiceViewSet,basename='services')
# router.register(r'Locksmithservices', LocksmithServiceViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'servicerequests', ServiceRequestViewSet)  # Add ServiceRequest viewset
router.register(r'servicebids', ServiceBidViewSet)  # Add ServiceBid viewset
router.register(r'adminsettings', AdminSettingsViewSet)
router.register(r'admincomission', AdmincomissionViewSet, basename='admincomission')
router.register(r'customer_service_requests', CustomerServiceRequestViewSet, basename='service_request')
router.register(r'admin/services', AdminLocksmithServiceViewSet, basename='admin-service')
router.register(r'admin/service-approval', AdminLocksmithServiceApprovalViewSet, basename='service-approval')
router.register(r'bookings', BookingViewSet)
router.register(r'customer-profile', CustomerProfileViewSet, basename='customer-profile')
router.register(r'contact', ContactMessageViewSet, basename='contact')
router.register(r'forgot-password', ForgotPasswordViewSet, basename='forgot-password')
# router.register(r'locksmithservices', LocksmithServiceUpdateViewSet, basename='locksmithservices')
# Add AdminSettings viewset

# URL patterns
urlpatterns = [
    path('', include(router.urls)),
    
]
