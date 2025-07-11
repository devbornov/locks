from rest_framework import viewsets, permissions , filters
from .permissions import IsAdmin
import csv
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Service, AdminSettings , ContactMessage
from .serializers import AdminSettingsSerializer, CustomerServiceRequestSerializer ,LocksmithCreateSerializer
from .models import User, Locksmith, CarKeyDetails, Service, Transaction, ServiceRequest, ServiceBid ,CustomerServiceRequest , Customer , AdminService,LocksmithServices , Booking
from .serializers import UserSerializer, LocksmithSerializer, CarKeyDetailsSerializer, ServiceSerializer, TransactionSerializer, ServiceRequestSerializer, ServiceBidSerializer,LocksmithServiceSerializer
from .serializers import UserCreateSerializer , CustomerSerializer , AdminServiceSerializer , BookingSerializer  , ContactMessageSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from django.contrib.auth import authenticate
import pyotp
from rest_framework import serializers
from django.core.mail import send_mail
from decimal import Decimal
from django.db import connection
from django.db.models import FloatField, F
from django.db.models.expressions import RawSQL
from math import radians
from django.http import JsonResponse
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from geopy.distance import geodesic
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import HttpResponse
from twilio.rest import Client   
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import os




class CreateAdminUserView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]  # Only authenticated admin users can create other users

    def post(self, request):
        # Validate and create a new admin user
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save(is_staff=True)  # Set user as admin (staff)
            return Response({"message": "user created successfully", "user": serializer.data})
        return Response(serializer.errors, status=400)
    
    
# User Registration API
class UserRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)

            totp_details = serializer.get_totp_details(user)

            # ✅ Get Latitude & Longitude from Request (Optional)
            latitude = request.data.get('latitude', None)
            longitude = request.data.get('longitude', None)

            # ✅ Only create a Customer profile if the user is a 'customer'
            if user.role == "customer":
                Customer.objects.create(user=user, latitude=latitude, longitude=longitude)

            return Response({
                'message': 'User registered successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'totp_enabled': user.totp_enabled,
                    'totp_secret': totp_details["totp_secret"],
                    'totp_qr_code': totp_details["totp_qr_code"],
                    'totp_qr_code_url': totp_details["qr_code_url"],
                },
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    
    
class CustomerProfileViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'put']  # ✅ Ensure `PUT` is allowed

    def get_queryset(self):
        """Ensure only the logged-in customer can access their profile"""
        return Customer.objects.filter(user=self.request.user)

    def get_object(self):
        """Return the logged-in user's customer profile"""
        return self.request.user.customer_profile

    def update(self, request, *args, **kwargs):
        """Update the logged-in customer's profile"""
        customer = self.get_object()
        serializer = self.get_serializer(customer, data=request.data, partial=False)  # ✅ Full update

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Profile updated successfully", "customer": serializer.data}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# class LocksmithRegisterView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         serializer = LocksmithCreateSerializer(data=request.data)
#         if serializer.is_valid():
#             user = serializer.save()
#             user.set_password(request.data['password'])  # Hash password
#             user.role = 'locksmith'  # Explicitly set the role
#             user.save()

#             # Generate authentication tokens
#             refresh = RefreshToken.for_user(user)

#             # Generate TOTP details for Locksmith
#             totp_details = serializer.get_totp_details(user)

#             return Response({
#                 'message': 'Locksmith registered successfully. Please complete your profile.',
#                 'user': {
#                     'id': user.id,
#                     'username': user.username,
#                     'email': user.email,
#                     'role': user.role,
#                     'totp_enabled': user.totp_enabled,
#                     'totp_secret': totp_details["totp_secret"],  # TOTP Key in Response
#                     'totp_qr_code': totp_details["totp_qr_code"],  # Base64 QR Code
#                     'totp_qr_code_url': totp_details["qr_code_url"],  # QR Image URL
#                 },
#                 'access': str(refresh.access_token),
#                 'refresh': str(refresh)
#             }, status=status.HTTP_201_CREATED)

#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class LocksmithRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LocksmithCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(request.data['password'])  # Hash password
            user.role = 'locksmith'  # Explicitly set the role
            user.save()

            # Generate authentication tokens
            refresh = RefreshToken.for_user(user)

            # Generate TOTP details
            totp_details = serializer.get_totp_details(user)

            # Send admin notification email
            self.send_admin_notification_email(user)

            return Response({
                'message': 'Locksmith registered successfully. Please complete your profile.',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'totp_enabled': user.totp_enabled,
                    'totp_secret': totp_details["totp_secret"],
                    'totp_qr_code': totp_details["totp_qr_code"],
                    'totp_qr_code_url': totp_details["qr_code_url"],
                },
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # def send_admin_notification_email(self, user):
    #     """🔔 Notify admin when a new locksmith registers"""
    #     subject = "New Locksmith Registration Notification"
    #     from_email = "contact@lockquick.com.au"
    #     recipient_list = ["contact@lockquick.com.au"]  # Replace with actual admin email(s)

    #     # Context for email template
    #     context = {
    #         'username': user.username,
    #         'email': user.email,
    #         'site_url': "https://admin.lockquick.com.au/admin",  # Adjust as needed
    #     }

    #     # Render email content
    #     html_content = render_to_string("emails/admin_locksmith_signup.html", context)
    #     text_content = strip_tags(html_content)

    #     email = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
    #     email.attach_alternative(html_content, "text/html")

    #     # Optional: Attach logo
    #     logo_path = os.path.join("static", "images", "logo.png")
    #     if os.path.exists(logo_path):
    #         with open(logo_path, "rb") as f:
    #             email.attach("logo.png", f.read(), "image/png")

    #     email.send()
    def send_admin_notification_email(self, user):
        """🔔 Notify admin + send welcome email to locksmith upon registration"""
        subject_admin = "New Locksmith Registration Notification"
        subject_user = "Welcome to LockQuick!"

        from_email = "contact@lockquick.com.au"
        admin_recipient = ["contact@lockquick.com.au"]  # Replace with actual admin email(s)
        user_recipient = [user.email]

        context = {
            'username': user.username,
            'email': user.email,
            'site_url': "https://admin.lockquick.com.au/admin",
        }

        # Render HTML templates
        html_admin = render_to_string("emails/admin_locksmith_signup.html", context)
        text_admin = strip_tags(html_admin)

        html_user = render_to_string("emails/locksmith_welcome_email.html", context)
        text_user = strip_tags(html_user)

        # --- Admin email ---
        admin_email = EmailMultiAlternatives(subject_admin, text_admin, from_email, admin_recipient)
        admin_email.attach_alternative(html_admin, "text/html")

        # --- User (locksmith) email ---
        user_email = EmailMultiAlternatives(subject_user, text_user, from_email, user_recipient)
        user_email.attach_alternative(html_user, "text/html")

        # Optional: Attach logo if it exists
        logo_path = os.path.join("static", "images", "logo.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                logo_data = f.read()
                admin_email.attach("logo.png", logo_data, "image/png")
                user_email.attach("logo.png", logo_data, "image/png")

        # Send emails
        admin_email.send()
        user_email.send()


    
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()  # Blacklist the refresh token

            return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)

        except Exception as e:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)    
    
    
class IsLocksmith(permissions.BasePermission):
    """
    Custom permission to allow only locksmiths to access the view.
    """

    def has_permission(self, request, view):
        # Ensure the user is authenticated and has the locksmith role
        return request.user and request.user.is_authenticated and request.user.role == "locksmith"
    
    
    
# class LocksmithProfileView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         """
#         Create a new locksmith profile for the logged-in user.
#         """
#         user = request.user

#         # Ensure the user is a locksmith
#         if user.role != 'locksmith':
#             return Response({"error": "Unauthorized. Only locksmiths can create profiles."}, status=status.HTTP_403_FORBIDDEN)

#         # Check if the locksmith profile already exists
#         if hasattr(user, 'locksmith'):
#             return Response({"error": "Profile already exists."}, status=status.HTTP_400_BAD_REQUEST)

#         # Create a new locksmith profile
#         serializer = LocksmithSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save(user=user)
#             return Response({"message": "Profile created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)

#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LocksmithProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.role != 'locksmith':
            return Response({"error": "Unauthorized. Only locksmiths can create profiles."}, status=status.HTTP_403_FORBIDDEN)

        if hasattr(user, 'locksmith'):
            return Response({"error": "Profile already exists."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = LocksmithSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=user)

            # Send notification to admin about new locksmith profile awaiting approval
            self.send_admin_notification_email(user)

            return Response({
                "message": "Profile created successfully. Waiting for admin approval.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def send_admin_notification_email(self, user):
        """🔔 Notify admin when a new locksmith registers"""
        subject = "New Locksmith Registration Notification - Awaiting Approval"
        from_email = "contact@lockquick.com.au"
        recipient_list = ["contact@lockquick.com.au"]  # Replace with your admin email(s)

        context = {
            'username': user.username,
            'email': user.email,
            'site_url': "https://admin.lockquick.com.au/admin",  # Admin panel URL
            'message': "A new locksmith profile has been created and is waiting for your approval."
        }

        html_content = render_to_string("emails/admin_locksmith_registered.html", context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
        email.attach_alternative(html_content, "text/html")

        logo_path = os.path.join("static", "images", "logo.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                email.attach("logo.png", f.read(), "image/png")

        email.send()

    def put(self, request):
        """
        Update an existing locksmith profile.
        """
        user = request.user

        try:
            locksmith = user.locksmith
        except Locksmith.DoesNotExist:
            return Response({"error": "Locksmith profile not found."}, status=status.HTTP_404_NOT_FOUND)

        # Convert request.data to mutable and remove gst_registered
        data = request.data.copy()
        data.pop('gst_registered', None)  # Prevent update of this field

        serializer = LocksmithSerializer(locksmith, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Profile updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class Approvalverification(viewsets.ModelViewSet):
    serializer_class = LocksmithSerializer
    permission_classes = [IsAuthenticated]  # Ensures only authenticated users can access

    def get_queryset(self):
        """
        Filter locksmith profiles by logged-in user.
        """
        user = self.request.user
        return Locksmith.objects.filter(user=user)  # Return only the locksmith profile of the logged-in user

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific locksmith profile by ID.
        """
        user = self.request.user
        locksmith_id = self.kwargs.get("pk")  # Get locksmith ID from the URL
        
        try:
            locksmith = Locksmith.objects.get(id=locksmith_id, user=user)
            serializer = self.get_serializer(locksmith)
            return Response(serializer.data)
        except Locksmith.DoesNotExist:
            return Response({"error": "Locksmith profile not found."}, status=404)
    
       


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        otp_code = request.data.get('otp_code', None)  # OTP input from user

        user = authenticate(username=username, password=password)
        if user is not None:
            # If TOTP is enabled, verify the OTP before allowing login
            if user.totp_secret:
                if not otp_code or not user.verify_totp(otp_code, valid_window=1):
                    return Response({'error': 'Invalid OTP'}, status=status.HTTP_401_UNAUTHORIZED)

            # Check if the user is a locksmith
            locksmith = None
            try:
                locksmith = Locksmith.objects.get(user=user)
                
                refresh = RefreshToken.for_user(user)
                # If the locksmith exists, check verification and approval status
                if not locksmith.is_verified:
                    return Response({
                        'message': 'Login successful',
                        'error': 'Your account is pending verification',
                        'user_id': user.id,
                        'username': user.username,
                        'role': user.role,
                        'is_locksmith': True,
                        'is_verified': False,
                        'is_approved': locksmith.is_approved,
                        'access': str(refresh.access_token),
                        'refresh': str(refresh)
                    }, status=status.HTTP_200_OK)

                if not locksmith.is_approved:
                    return Response({
                        'message': 'Login successful',
                        'error': 'Your account has been rejected',
                        'user_id': user.id,
                        'username': user.username,
                        'role': user.role,
                        'is_locksmith': True,
                        'is_verified': locksmith.is_verified,
                        'is_approved': False,
                        'access': str(refresh.access_token),
                        'refresh': str(refresh)
                    }, status=status.HTTP_200_OK)

            except Locksmith.DoesNotExist:
                pass  # User is not a locksmith

            # Generate authentication tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'message': 'Login successful',
                'user_id': user.id,
                'username': user.username,
                'role': user.role,
                'is_locksmith': True if locksmith else False,
                'is_verified': locksmith.is_verified if locksmith else None,
                'is_approved': locksmith.is_approved if locksmith else None,
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)



# # Custom Permissions
# class IsAdmin(permissions.BasePermission):
#     def has_permission(self, request, view):
#         user = request.user
#         return user.is_authenticated and getattr(user, 'role', None) == 'admin'

# class IsLocksmith(permissions.BasePermission):
#     def has_permission(self, request, view):
#         return request.user.role == 'locksmith'  # Adjust role check for locksmiths

# class IsCustomer(permissions.BasePermission):
#     def has_permission(self, request, view):
#         return request.user.is_authenticated and getattr(request.user, 'role', None) == 'customer'  # Adjust role check for customers
    
    
# class IsAdminOrCustomer(permissions.BasePermission):
#     def has_permission(self, request, view):
#         return request.user.role in ['admin', 'customer']
    
    
    
# class IsAdminOrLocksmith(permissions.BasePermission):
#     def has_permission(self, request, view):
#         return request.user.role in ['admin', 'locksmith']



class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and getattr(user, 'role', None) == 'admin'


class IsLocksmith(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and getattr(user, 'role', None) == 'locksmith'


class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and getattr(user, 'role', None) == 'customer'


class IsAdminOrCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and getattr(user, 'role', None) in ['admin', 'customer']


class IsAdminOrLocksmith(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and getattr(user, 'role', None) in ['admin', 'locksmith']



# Admin Views
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]  # Only Admin can manage users
    
    
    
class CustomersViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(role='customer')
    serializer_class = UserSerializer
    permission_classes = [IsAdmin] 
    
class AllLocksmiths(viewsets.ReadOnlyModelViewSet):  # Use ReadOnlyModelViewSet if only listing
    queryset = User.objects.filter(role='locksmith')
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    

class CarKeyDetailsViewSet(viewsets.ModelViewSet):
    queryset = CarKeyDetails.objects.all()
    serializer_class = CarKeyDetailsSerializer
    # permission_classes = [IsAdmin]
    filter_backends = [filters.SearchFilter]
    search_fields = ['manufacturer']
    
from rest_framework.permissions import AllowAny
from django.db.models import Q
class CusCarKeyDetailsViewSet(viewsets.ModelViewSet):
    serializer_class = CarKeyDetailsSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['manufacturer', 'model', 'year_from', 'year_to', 'number_of_buttons']

    def get_queryset(self):
        queryset = CarKeyDetails.objects.all()
        target_year = self.request.query_params.get('year')
        if target_year:
            try:
                year = int(target_year)
                queryset = queryset.filter(
                    Q(year_from__lte=year) & Q(year_to__gte=year)
                )
            except ValueError:
                pass  # Ignore invalid input
        return queryset




class AdminLocksmithServiceApprovalViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        service = get_object_or_404(LocksmithServices, pk=pk)
        service.approved = True
        service.save()
        return Response({"status": "Service approved"})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        service = get_object_or_404(LocksmithServices, pk=pk)
        service.delete()
        return Response({"status": "Service rejected"})

class AdminLocksmithServiceViewSet(viewsets.ModelViewSet):
    """
    Admin can manage services that locksmiths can choose from.
    """
    queryset = AdminService.objects.all()
    serializer_class = AdminServiceSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['get'])
    def list_approved_services(self, request):
        """Get all services that are approved by the admin"""
        approved_services = LocksmithServices.objects.filter(approved=True)
        serializer = LocksmithServiceSerializer(approved_services, many=True)
        return Response(serializer.data)
    
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def services_to_customer(self, request):
        """
        Get all approved locksmith services,
        optionally filtered by service type and sorted by distance.
        Adds service_area, gst_registered, is_available to the response.
        """

        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        service_type = request.query_params.get('service_type', None)

        if not latitude or not longitude:
            return Response({"error": "Latitude and Longitude are required"}, status=400)

        latitude, longitude = float(latitude), float(longitude)

        # Filter only approved services
        approved_services = LocksmithServices.objects.filter(approved=True)

        # Apply filtering if service_type is provided
        if service_type:
            approved_services = approved_services.filter(service_type=service_type)

        # Calculate distance for each locksmith and filter accordingly
        locksmith_services_with_distance = []

        for service in approved_services:
            locksmith = service.locksmith  # Assuming `locksmith` is a ForeignKey in `LocksmithServices`
            locksmith_location = (locksmith.latitude, locksmith.longitude)
            customer_location = (latitude, longitude)
            distance_km = geodesic(customer_location, locksmith_location).km

            # Serialize service data
            service_data = LocksmithServiceSerializer(service).data

            # Ensure car_key_details appears only once
            car_key_details = service_data.pop("car_key_details", None)

            # Build response item
            locksmith_services_with_distance.append({
                "locksmith": locksmith.user.username,
                "latitude": locksmith.latitude,
                "longitude": locksmith.longitude,
                "distance_km": round(distance_km, 2),
                "service_area": locksmith.service_area,             # ✅ added
                "gst_registered": locksmith.gst_registered,         # ✅ added
                "is_available": locksmith.is_available,             # ✅ added
                "service": service_data,
                "car_key_details": car_key_details
            })

        # Sort by nearest distance
        locksmith_services_with_distance.sort(key=lambda x: x["distance_km"])

        return Response(locksmith_services_with_distance)


    
    
    # @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    # def available_services(self, request):
    #     """
    #     Get all services added by the admin so the logged-in locksmith can choose.
    #     """
    #     services = AdminService.objects.all()
    #     serializer = AdminServiceSerializer(services, many=True)
    #     return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def available_services(self, request):
        """
        Get all services added by the admin so the logged-in locksmith can choose.
        Supports optional filtering by service_type.
        """
        service_type = request.query_params.get('service_type')
        services = AdminService.objects.all()
        if service_type:
            services = services.filter(service_type=service_type)
        serializer = AdminServiceSerializer(services, many=True)
        return Response(serializer.data)


    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def all_locksmith_services(self, request):
        """
        Admin can view all services added by locksmiths (both approved and pending).
        """
        services = LocksmithServices.objects.all()
        serializer = LocksmithServiceSerializer(services, many=True)
        return Response(serializer.data)
    
    
    
    def destroy(self, request, pk=None):
        """Delete an admin service"""
        service = get_object_or_404(AdminService, pk=pk)
        service.delete()
        return Response({"status": "Service deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
    
    
class ServiceViewSet(viewsets.ModelViewSet):
    serializer_class = LocksmithServiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only services belonging to the logged-in locksmith."""
        user = self.request.user
        try:
            locksmith = user.locksmith  # Ensure user is linked to a Locksmith
            return LocksmithServices.objects.filter(locksmith=locksmith)
        except AttributeError:
            return LocksmithServices.objects.none()  # Return empty if not a locksmith

    
    # def perform_create(self, serializer):
    #     user = self.request.user

    #     if not hasattr(user, "locksmith"):
    #         raise serializers.ValidationError({"error": "User is not associated with a locksmith account."})

    #     locksmith = user.locksmith

    #     admin_settings = AdminSettings.objects.first()
    #     if not admin_settings:
    #         raise serializers.ValidationError({"error": "Admin settings not configured."})

    #     commission_amount = admin_settings.commission_amount or Decimal("0")
    #     percentage = admin_settings.percentage or Decimal("0")

    #     custom_price = Decimal(str(serializer.validated_data.get("custom_price", "0.00")))
    #     additional_key_price = Decimal(str(serializer.validated_data.get("additional_key_price", "0.00")))

    #     percentage_amount = (custom_price * percentage) / Decimal("100")
    #     total_price = custom_price + percentage_amount + commission_amount

    #     service_type = serializer.validated_data.get("service_type", "residential")
    #     car_key_details_data = self.request.data.get("car_key_details", None)

    #     if service_type == "automotive":
    #         if not car_key_details_data or not isinstance(car_key_details_data, dict):
    #             raise serializers.ValidationError({"error": "Car key details must be provided as a dictionary for automotive services."})

    #         car_key_details = CarKeyDetails.objects.create(
    #             manufacturer=car_key_details_data.get("manufacturer"),
    #             model=car_key_details_data.get("model"),
    #             year_from=car_key_details_data.get("year_from"),
    #             year_to=car_key_details_data.get("year_to"),
    #             number_of_buttons=car_key_details_data.get("number_of_buttons")
    #         )

    #         serializer.save(
    #             locksmith=locksmith,
    #             total_price=total_price,
    #             approved=False,
    #             car_key_details=car_key_details
    #         )
    #     else:
    #         serializer.save(
    #             locksmith=locksmith,
    #             total_price=total_price,
    #             approved=False
    #         )
    
    def perform_create(self, serializer):
        user = self.request.user

        if not hasattr(user, "locksmith"):
            raise serializers.ValidationError({"error": "User is not associated with a locksmith account."})

        locksmith = user.locksmith

        admin_settings = AdminSettings.objects.first()
        if not admin_settings:
            raise serializers.ValidationError({"error": "Admin settings not configured."})

        commission_amount = admin_settings.commission_amount or Decimal("0.00")
        percentage = admin_settings.percentage or Decimal("0.00")

        base_price = Decimal(str(serializer.validated_data.get("custom_price", "0.00")))
        subtotal = base_price
        percentage_amount = (subtotal * percentage) / Decimal("100")
        total_price = subtotal + percentage_amount + commission_amount

        service_type = serializer.validated_data.get("service_type", "residential")
        car_key_details_data = self.request.data.get("car_key_details", None)

        if service_type == "automotive":
            if not car_key_details_data or not isinstance(car_key_details_data, dict):
                raise serializers.ValidationError({"error": "Car key details must be provided as a dictionary for automotive services."})

            car_key_details = CarKeyDetails.objects.create(
                manufacturer=car_key_details_data.get("manufacturer"),
                model=car_key_details_data.get("model"),
                year_from=car_key_details_data.get("year_from"),
                year_to=car_key_details_data.get("year_to"),
                number_of_buttons=car_key_details_data.get("number_of_buttons")
            )

            serializer.save(
                locksmith=locksmith,
                total_price=total_price,
                approved=False,
                car_key_details=car_key_details
            )
        else:
            serializer.save(
                locksmith=locksmith,
                total_price=total_price,
                approved=False
            )

        # Send admin notification email using your detailed method
        self.send_admin_notification_email(user=locksmith.user, service_type=service_type, base_price=base_price, total_price=total_price)

    def send_admin_notification_email(self, user, service_type, base_price, total_price):
        """🔔 Notify admin when a new locksmith service is created"""
        subject = "New Locksmith Service Submitted"
        from_email = "contact@lockquick.com.au"
        recipient_list = ["contact@lockquick.com.au"]  # Replace with your admin email(s)

        context = {
            'username': user.username,
            'email': user.email,
            'site_url': "https://admin.lockquick.com.au/admin",  # Admin panel URL
            'service_type': service_type,
            'base_price': base_price,
            'total_price': total_price,
            'message': "A new locksmith service has been submitted and is waiting for approval."
        }

        html_content = render_to_string("emails/admin_locksmith_service_submitted.html", context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
        email.attach_alternative(html_content, "text/html")

        logo_path = os.path.join("static", "images", "logo.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                email.attach("logo.png", f.read(), "image/png")

        email.send()


    
    


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAdmin]  # Only Admin can manage transactions

# Locksmith Views
class LocksmithDashboardViewSet(viewsets.GenericViewSet):
    permission_classes = [IsLocksmith]

    @action(detail=False, methods=['get'])
    def my_services(self, request):
        locksmith = Locksmith.objects.get(user=request.user)
        services = locksmith.services_offered.all()
        return Response(ServiceSerializer(services, many=True).data)

    @action(detail=False, methods=['get'])
    def my_transactions(self, request):
        locksmith = Locksmith.objects.get(user=request.user)
        transactions = Transaction.objects.filter(locksmith=locksmith)
        return Response(TransactionSerializer(transactions, many=True).data)

    @action(detail=False, methods=['put'])
    def update_service_prices(self, request):
        locksmith = Locksmith.objects.get(user=request.user)
        # Logic for updating prices
        return Response({'status': 'prices updated'})

class ServiceRequestViewSet(viewsets.ModelViewSet):
    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestSerializer
    permission_classes = [IsLocksmith]  # Locksmiths can manage service requests

    @action(detail=True, methods=['put'], permission_classes=[IsLocksmith])
    def accept_request(self, request, pk=None):
        service_request = self.get_object()
        service_request.status = 'ACCEPTED'
        service_request.save()
        return Response({'status': 'request accepted'})

    @action(detail=True, methods=['put'], permission_classes=[IsLocksmith])
    def reject_request(self, request, pk=None):
        service_request = self.get_object()
        service_request.status = 'REJECTED'
        service_request.save()
        return Response({'status': 'request rejected'})
    
class AdminSettingsViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]
    queryset = AdminSettings.objects.all()
    serializer_class = AdminSettingsSerializer    
    
    
    


class AdmincomissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for updating or creating the admin percentage settings.
    Only accessible by Admins.
    """
    queryset = AdminSettings.objects.all()
    serializer_class = AdminSettingsSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def update(self, request, *args, **kwargs):
        """
        Update the first existing AdminSettings record or create one if none exists.
        """
        admin_settings = AdminSettings.objects.first()  # Fetch the first record

        percentage = request.data.get("percentage")
        commission_amount = request.data.get("commission_amount")

        if percentage is None or commission_amount is None:
            return Response({"error": "Both admin_percentage and commission_amount are required."}, 
                            status=status.HTTP_400_BAD_REQUEST)

        if admin_settings:
            # Update existing record
            admin_settings.percentage = percentage
            admin_settings.commission_amount = commission_amount
            admin_settings.save()
            message = "Admin settings updated successfully."
        else:
            # Create new record only if none exists
            admin_settings = AdminSettings.objects.create(
                percentage=percentage, 
                commission_amount=commission_amount
            )
            message = "Admin settings created successfully."

        return Response({
            "message": message,
            "percentage": admin_settings.percentage,
            "commission_amount": admin_settings.commission_amount
        }, status=status.HTTP_200_OK)





class ServiceBidViewSet(viewsets.ModelViewSet):
    queryset = ServiceBid.objects.all()
    serializer_class = ServiceBidSerializer
    permission_classes = [IsCustomer]  # Customers can place bids

    @action(detail=True, methods=['post'], permission_classes=[IsCustomer])
    def place_bid(self, request, pk=None):
        service_request = self.get_object()
        bid_amount = request.data.get('bid_amount')
        # Add logic for bid creation, and validation
        return Response({'status': 'bid placed'})

# Customer Views
class CustomerDashboardViewSet(viewsets.GenericViewSet):
    permission_classes = [IsCustomer]

    @action(detail=False, methods=['get'])
    def available_locksmiths(self, request):
        locksmiths = Locksmith.objects.filter(is_approved=True)
        return Response(LocksmithSerializer(locksmiths, many=True).data)

    @action(detail=False, methods=['get'])
    def my_bids(self, request):
        customer = User.objects.get(username=request.user.username)
        bids = ServiceBid.objects.filter(customer=customer)
        return Response(ServiceBidSerializer(bids, many=True).data)

    @action(detail=False, methods=['post'])
    def place_service_request(self, request):
        # Logic for creating service requests
        return Response({'status': 'service request placed'})



            
            
class CustomerServiceRequestViewSet(viewsets.ModelViewSet):
    queryset = CustomerServiceRequest.objects.all()
    serializer_class = CustomerServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter requests based on user role"""
        user = self.request.user
        queryset = CustomerServiceRequest.objects.all()

        # 🔹 Customers see only their requests
        if user.role == 'customer':
            queryset = queryset.filter(customer__user=user)

        # 🔹 Locksmiths see only assigned requests
        elif user.role == 'locksmith':
            queryset = queryset.filter(locksmith__user=user)

        # 🔹 Distance-based filtering (for customers)
        user_lat = self.request.query_params.get('latitude')
        user_lon = self.request.query_params.get('longitude')

        if user_lat and user_lon:
            user_location = Point(float(user_lon), float(user_lat), srid=4326)
            queryset = queryset.annotate(distance=Distance('locksmith__location', user_location)).order_by('distance')

        return queryset

    def perform_create(self, serializer):
        """Assign customer and trigger WebSocket update"""
        customer = get_object_or_404(Customer, user=self.request.user)
        service_request = serializer.save(customer=customer)

        # 🔹 Notify WebSocket clients
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "service_requests",
            {"type": "service_request_update", "data": {"message": "New service request created"}}
        )

    def partial_update(self, request, *args, **kwargs):
        """Allow only locksmiths to update status and trigger WebSocket update"""
        service_request = self.get_object()

        if service_request.locksmith.user != request.user:
            return Response({"error": "Only the assigned locksmith can update this request."}, status=403)

        new_status = request.data.get('status')
        if new_status in ['accepted', 'rejected', 'completed']:
            service_request.status = new_status
            service_request.save()

            # 🔹 Notify WebSocket clients
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "service_requests",
                {"type": "service_request_update", "data": {"message": f"Request {service_request.id} updated to {new_status}"}}
            )

            return Response({"message": f"Service request updated to {new_status}."})
        
        return Response({"error": "Invalid status update."}, status=400)
    
    
    
   
    
    
    
    
    
import stripe
from django.conf import settings
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Locksmith    
    
stripe.api_key = settings.STRIPE_SECRET_KEY  # Use your Stripe Secret Key

class LocksmithViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Locksmiths:
    - Admin approval/rejection
    - Stripe Account creation & onboarding
    - Checking onboarding status
    """
    queryset = Locksmith.objects.all()
    serializer_class = LocksmithSerializer
    permission_classes = [IsAdminUser]  # Only Admin can manage locksmiths

    # ✅ Verify Locksmith (Admin Only)
    @action(detail=True, methods=['put'], permission_classes=[IsAdminUser])
    def verify_locksmith(self, request, pk=None):
        locksmith = self.get_object()
        locksmith.is_verified = True
        locksmith.is_approved = True  # Approve upon verification
        locksmith.save()

        # 🔹 Send email notification
        self.send_verification_email(locksmith)

        return Response({'status': 'Locksmith verified', 'locksmith_data': LocksmithSerializer(locksmith).data})

    def send_verification_email(self, locksmith):
        """✅ Sends email notification when locksmith gets verified"""
        subject = "Your Locksmith Account is Verified!"
        from_email = "contact@lockquick.com.au"  # Replace with your email
        recipient_list = [locksmith.user.email]

        # Render HTML email template
        context = {
            'locksmith_name': locksmith.user.username,
            'site_url': "https://lockquick.com.au/lock-dashboard/",  # Update with live URL
        }
        html_content = render_to_string("emails/locksmith_verified.html", context)
        text_content = strip_tags(html_content)  # Fallback text email

        email = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
        email.attach_alternative(html_content, "text/html")

        # Attach logo (assuming it's in static folder)
        logo_path = os.path.join("static", "images", "logo.png")  # Update path as needed
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                email.attach("logo.png", f.read(), "image/png")

        email.send()
        
        
    # ✅ Reject Locksmith (Admin Only)
    @action(detail=True, methods=['put'], permission_classes=[IsAdminUser])
    def reject_locksmith(self, request, pk=None):
        locksmith = self.get_object()
        locksmith.is_verified = False
        locksmith.is_approved = False
        locksmith.save()

        # 🔹 Send rejection email notification
        self.send_rejection_email(locksmith)

        return Response({'status': 'Locksmith rejected', 'locksmith_data': LocksmithSerializer(locksmith).data})

    def send_rejection_email(self, locksmith):
        """❌ Sends email notification when locksmith gets rejected"""
        subject = "Your Locksmith Application Has Been Rejected"
        from_email = "contact@lockquick.com.au"  # Replace with your email
        recipient_list = [locksmith.user.email]

        # Render HTML email template
        context = {
            'locksmith_name': locksmith.user.username,
            'support_email': "contact@lockquick.com.au"  # Replace with your support email
        }
        html_content = render_to_string("emails/locksmith_rejected.html", context)
        text_content = strip_tags(html_content)  # Fallback text email

        email = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
        email.attach_alternative(html_content, "text/html")

        # Attach logo (assuming it's in static folder)
        logo_path = os.path.join("static", "images", "logo.png")  # Update path as needed
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                email.attach("logo.png", f.read(), "image/png")

        email.send()

    # ✅ View Locksmith Details (Admin Only)
    @action(detail=True, methods=['get'], permission_classes=[IsAdminUser])
    def verify_locksmith_details(self, request, pk=None):
        locksmith = self.get_object()
        return Response(LocksmithSerializer(locksmith).data)

    @action(detail=False, methods=['get'], permission_classes=[IsLocksmith])
    def locksmithform_val(self, request):
        locksmith = Locksmith.objects.get(user=request.user)  # Get locksmith linked to the logged-in user
        return Response(LocksmithSerializer(locksmith).data)
    
    # @action(detail=False, methods=['get'], permission_classes=[IsLocksmith])
    # def locksmithform_val(self, request):
    #     try:
    #         locksmith = Locksmith.objects.get(user=request.user)
    #     except Locksmith.DoesNotExist:
    #         return Response({
    #             "detail": "User not found",
    #             "code": "user_not_found"
    #         }, status=status.HTTP_404_NOT_FOUND)

    #     serializer = LocksmithSerializer(locksmith)
    #     return Response(serializer.data, status=status.HTTP_200_OK)


    # ✅ Create Stripe Express Account for Locksmith
    @action(detail=False, methods=['post'], permission_classes=[IsLocksmith])
    def create_stripe_account(self, request):
        locksmith = request.user.locksmith  # Get the locksmith from the logged-in user

        if locksmith.stripe_account_id:
            return Response({"message": "Stripe account already exists!", "stripe_account_id": locksmith.stripe_account_id})

        # Create a Stripe Express account
        stripe_account = stripe.Account.create(
            type="express",
            country="AU",  # Change based on your country
            email=locksmith.user.email,
            capabilities={"card_payments": {"requested": True}, "transfers": {"requested": True}},
        )

        # Save Stripe Account ID
        locksmith.stripe_account_id = stripe_account.id
        locksmith.save()

        return Response({"message": "Stripe account created!", "stripe_account_id": stripe_account.id})

    # ✅ Generate Stripe Onboarding Link & Send Email
    @action(detail=False, methods=['get'], permission_classes=[IsLocksmith])
    def generate_stripe_onboarding_link(self, request):
        locksmith = request.user.locksmith  # Get the locksmith from the logged-in user

        if not locksmith.stripe_account_id:
            return Response({"error": "Locksmith does not have a Stripe account."}, status=400)

        account_link = stripe.AccountLink.create(
            account=locksmith.stripe_account_id,
            refresh_url="https://lockquick.com.au/stripe-onboard",
            return_url="https://lockquick.com.au/lock-dashboard",
            type="account_onboarding",
        )

        # Send onboarding link via email
        send_mail(
            "Complete Your Stripe Verification",
            f"Hello {locksmith.user.username},\n\nPlease complete your Stripe account setup by clicking the link below:\n\n{account_link.url}\n\nThanks!",
            "your_email@example.com",  # Replace with your email
            [locksmith.user.email],
            fail_silently=False,
        )

        return Response({"message": "Onboarding link sent to locksmith's email!", "onboarding_url": account_link.url})

    # ✅ Check Stripe Onboarding Status
    @action(detail=False, methods=['get'], permission_classes=[IsLocksmith])
    def check_onboarding_status(self, request):
        locksmith = request.user.locksmith  # Get the locksmith from the logged-in user

        if not locksmith.stripe_account_id:
            return Response({"error": "You do not have a Stripe account."}, status=400)

        stripe_account = stripe.Account.retrieve(locksmith.stripe_account_id)

        return Response({
            "email": stripe_account.email,
            "payouts_enabled": stripe_account.payouts_enabled,
            "charges_enabled": stripe_account.charges_enabled,
            "requirements": stripe_account.requirements,
        })
        
        
    @action(detail=False, methods=['get'], permission_classes=[IsLocksmith])
    def generate_stripe_login_link(self, request):
        locksmith = request.user.locksmith

        if not locksmith.stripe_account_id:
            return Response({"error": "You do not have a Stripe account."}, status=400)

        # Generate login link
        login_link = stripe.Account.create_login_link(locksmith.stripe_account_id)

        return Response({"login_url": login_link.url})
        
        
        
        
    @action(detail=False, methods=['post'], permission_classes=[IsLocksmith])
    def mark_open_to_work(self, request):
        """✅ Locksmith sets themselves as available for new jobs"""
        locksmith = get_object_or_404(Locksmith, user=request.user)

        locksmith.is_available = True
        locksmith.save()
        return Response({"status": "Locksmith is now available for new jobs."})

    @action(detail=False, methods=['post'], permission_classes=[IsLocksmith])
    def mark_not_available(self, request):
        """✅ Locksmith marks themselves as unavailable (busy)"""
        locksmith = get_object_or_404(Locksmith, user=request.user)

        locksmith.is_available = False
        locksmith.save()
        return Response({"status": "Locksmith is now unavailable."})
    
    
    
    
    def send_discount_email(self, locksmith, is_discounted):
        subject = "You've received a platform discount!" if is_discounted else "Your discount has been removed"
        from_email = "contact@lockquick.com.au"  # Update with your verified sender
        recipient_list = [locksmith.user.email]

        context = {
            'locksmith_name': locksmith.user.username,
            'discount_status': "enabled" if is_discounted else "removed",
            'dashboard_url': "https://lockquick.com.au/lock-dashboard/",  # Update as needed
        }

        # Render email content
        html_content = render_to_string("emails/locksmith_discount_status.html", context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
        email.attach_alternative(html_content, "text/html")

        # Optionally attach logo
        logo_path = os.path.join("static", "images", "logo.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                email.attach("logo.png", f.read(), "image/png")

        email.send()
        
    
    
    @action(detail=True, methods=['put'], permission_classes=[IsAdminUser])
    def toggle_discount(self, request, pk=None):
        locksmith = self.get_object()
        incoming_value = request.data.get("is_discounted")

        # Update discount status
        if incoming_value is not None:
            locksmith.is_discounted = bool(incoming_value)
        else:
            locksmith.is_discounted = not locksmith.is_discounted  # fallback to toggle

        locksmith.save()

        # Set status label
        status = "enabled" if locksmith.is_discounted else "disabled"

        # ✅ Send email notification
        self.send_discount_email(locksmith, locksmith.is_discounted)

        return Response({
            "status": f"Discount {status} for {locksmith.user.username}",
            "is_discounted": locksmith.is_discounted
        })

        
      
        


from twilio.rest import Client

TWILIO_ACCOUNT_SID = "ACb9993d68e0c490eb54de4f61018d5691"
TWILIO_AUTH_TOKEN = "6e7b89c3e473c1a92a9d31e6868fee66"
TWILIO_PHONE_NUMBER = "+12185229562"

def send_sms(to_phone, message):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    sms = client.messages.create(
        body=message,
        from_=TWILIO_PHONE_NUMBER,
        to=to_phone
    )
    print(f"📩 SMS sent to {to_phone} - SID: {sms.sid}")
    return sms.sid





class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling bookings, payments, refunds, and status updates.
    """
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated] 
    
    def get_queryset(self):
        user = self.request.user
        payment_status = self.request.query_params.get("payment_status")
        emergency = self.request.query_params.get("emergency")

        bookings = Booking.objects.none()

        if user.role == "customer":
            bookings = Booking.objects.filter(customer=user)

        elif user.role == "locksmith":
            try:
                locksmith = Locksmith.objects.get(user=user)
                bookings = Booking.objects.filter(locksmith_service__locksmith=locksmith)
            except Locksmith.DoesNotExist:
                return Booking.objects.none()

        elif user.role == "admin":
            bookings = Booking.objects.all()

        # Apply filters if provided
        if payment_status:
            bookings = bookings.filter(payment_status=payment_status)

        if emergency in ["true", "false"]:
            bookings = bookings.filter(emergency=(emergency.lower() == "true"))

        # ✅ Explicitly order by ID (ascending)
        return bookings.order_by('id')
        

    
    # def perform_create(self, serializer):
    #     user = self.request.user

    #     if not user.is_authenticated:
    #         raise serializers.ValidationError({"error": "User must be authenticated to create a booking."})

    #     if user.role != "customer":
    #         raise serializers.ValidationError({"error": "Only customers can create bookings."})

    #     data = self.request.data
    #     locksmith_service_id = data.get('locksmith_service')
    #     try:
    #         locksmith_service = LocksmithServices.objects.get(id=locksmith_service_id)
    #     except LocksmithServices.DoesNotExist:
    #         raise serializers.ValidationError({"error": "Invalid locksmith service."})

    #     number_of_keys = int(data.get('number_of_keys', 0))
    #     additional_key_price = locksmith_service.additional_key_price or Decimal("0.00")

    #     admin_settings = AdminSettings.objects.first()
    #     if not admin_settings:
    #         raise serializers.ValidationError({"error": "Admin settings not configured."})

    #     commission_amount = admin_settings.commission_amount or Decimal("0.00")
    #     percentage = admin_settings.percentage or Decimal("0.00")
    #     gst_percentage = admin_settings.gst_percentage or Decimal("0.00")

    #     base_price = locksmith_service.custom_price or Decimal("0.00")
    #     keys_total = number_of_keys * additional_key_price

    #     subtotal = base_price + keys_total

    #     percentage_amount = (subtotal * percentage) / Decimal("100")
    #     platform_income = commission_amount + percentage_amount

    #     gst_amount = (platform_income * gst_percentage) / Decimal("100")

    #     total_price = subtotal + platform_income + gst_amount

    #     # Get emergency value from request (default to False if not provided)
    #     emergency = data.get('emergency', False)
    #     if isinstance(emergency, str):
    #         emergency = emergency.lower() in ['true', '1', 'yes']  # Convert string to boolean

    #     serializer.save(
    #         customer=user,
    #         locksmith_service=locksmith_service,
    #         number_of_keys=number_of_keys,
    #         total_price=total_price,
    #         emergency=emergency
    #     )



    def perform_create(self, serializer):
        user = self.request.user

        if not user.is_authenticated:
            raise serializers.ValidationError({"error": "User must be authenticated to create a booking."})

        if user.role != "customer":
            raise serializers.ValidationError({"error": "Only customers can create bookings."})

        data = self.request.data
        locksmith_service_id = data.get('locksmith_service')

        try:
            locksmith_service = LocksmithServices.objects.get(id=locksmith_service_id)
        except LocksmithServices.DoesNotExist:
            raise serializers.ValidationError({"error": "Invalid locksmith service."})

        number_of_keys = int(data.get('number_of_keys', 0))
        additional_key_price = locksmith_service.additional_key_price or Decimal("0.00")

        # Admin Fee Settings
        admin_settings = AdminSettings.objects.first()
        if not admin_settings:
            raise serializers.ValidationError({"error": "Admin settings not configured."})

        commission_amount = admin_settings.commission_amount or Decimal("0.00")
        percentage = admin_settings.percentage or Decimal("0.00")
        gst_percentage = admin_settings.gst_percentage or Decimal("0.00")

        # Price Calculations
        base_price = locksmith_service.custom_price or Decimal("0.00")
        keys_total = number_of_keys * additional_key_price
        subtotal = base_price + keys_total

        locksmith = locksmith_service.locksmith

        # ✅ Waive 10% percentage fee if locksmith is discounted
        if locksmith.is_discounted:
            percentage_amount = Decimal("0.00")
        else:
            percentage_amount = (subtotal * percentage) / Decimal("100")

        platform_fee = commission_amount + percentage_amount
        gst_amount = (platform_fee * gst_percentage) / Decimal("100")
        total_price = subtotal + platform_fee + gst_amount

        # Convert emergency field
        emergency = data.get('emergency', False)
        if isinstance(emergency, str):
            emergency = emergency.lower() in ['true', '1', 'yes']

        # Save only what's in the Booking model
        serializer.save(
            customer=user,
            locksmith_service=locksmith_service,
            number_of_keys=number_of_keys,
            total_price=total_price,
            emergency=emergency,
            customer_contact_number=data.get('customer_contact_number', ''),
            customer_address=data.get('customer_address', ''),
            house_number=data.get('house_number', '')
        )

            

    
    @action(detail=True, methods=['post'],permission_classes=[IsCustomer])
    def process_payment(self, request, pk=None):
        booking = self.get_object()

        # Use total_price directly from the booking model
        total_price = booking.total_price or 0.0
        locksmith_service = booking.locksmith_service

        if total_price <= 0:
            return Response({"error": "Total price must be greater than 0."}, status=400)

        try:
            # Stripe checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card", "afterpay_clearpay", "klarna", "zip"],
                line_items=[{
                    'price_data': {
                        'currency': 'aud',
                        'product_data': {
                            'name': locksmith_service.admin_service.name
                        },
                        'unit_amount': int(total_price * 100),  # Stripe uses cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url="https://lockquick.com.au/payment-success?session_id={CHECKOUT_SESSION_ID}",
                # success_url="http://localhost:3000/payment-success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="https://lockquick.com.au/payment-cancel",
            )

            booking.stripe_session_id = checkout_session.id
            booking.payment_status = "pending"
            booking.save()

            return Response({'checkout_url': checkout_session.url})

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)

    


    @action(detail=True, methods=['post'],permission_classes=[IsCustomer])
    def complete_payment(self, request, pk=None):
        booking = self.get_object()

        if not booking.stripe_session_id:
            return Response({"error": "Missing Stripe Session ID."}, status=400)

        try:
            session = stripe.checkout.Session.retrieve(booking.stripe_session_id)

            if session.payment_status == "paid":
                booking.payment_intent_id = session.payment_intent
                booking.payment_status = "paid"
                booking.status = "Scheduled"
                booking.save()

                locksmith = booking.locksmith_service.locksmith
                customer = booking.customer

                return Response({
                    "status": "Payment confirmed and booking scheduled.",
                    "message": "SMS notifications sent to customer and locksmith."
                })

            return Response({"error": "Payment is not completed yet."}, status=400)

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)
        
        
        
    @action(detail=True, methods=['post'], permission_classes=[IsLocksmith])
    def approve_booking(self, request, pk=None):
        booking = self.get_object()
        user = request.user

        if user.role != 'locksmith':
            return Response({'error': 'Only locksmiths can approve bookings.'}, status=403)

        if booking.locksmith_status != 'PENDING':
            return Response({'error': 'Booking has already been responded to.'}, status=400)

        if booking.payment_status != 'paid':
            return Response({'error': 'Cannot approve booking. Payment is not completed.'}, status=400)

        booking.locksmith_status = 'APPROVED'
        booking.save()

        customer = booking.customer
        locksmith = booking.locksmith_service.locksmith

        # Notify customer
        customer_message = (
            f"Hello {customer.get_full_name()},\n"
            f"Your booking (ID: {booking.id}) has been accepted by the locksmith.\n"
            f"Locksmith: {locksmith.user.get_full_name()}\n"
            f"Contact: {locksmith.contact_number}\n"
            f"Scheduled Date: {booking.scheduled_date.strftime('%Y-%m-%d %H:%M')}\n"
            f"Thank you for choosing our service!"
        )
        send_sms(booking.customer_contact_number or customer.phone_number, customer_message)

        # Notify locksmith again (optional)
        locksmith_message = (
            f"Hello {locksmith.user.get_full_name()},\n"
            f"Your approved service details are here:\n"
            f"Booking ID: {booking.id}\n"
            f"Customer: {customer.get_full_name()}\n"
            f"Service: {booking.locksmith_service.admin_service.name}\n"
            f"Customer Address: {booking.customer_address or 'N/A'}\n"
            f"Customer Phone: {booking.customer_contact_number or customer.phone_number or 'N/A'}\n"
            f"Scheduled Date: {booking.scheduled_date.strftime('%Y-%m-%d %H:%M')}\n"
            f"Emergency Service: {'Yes' if booking.emergency else 'No'}\n"
            f"Thank you.\n"
        )
        send_sms(locksmith.contact_number, locksmith_message)

        return Response({'status': 'Booking approved and customer notified.'})

    @action(detail=True, methods=['post'], permission_classes=[IsLocksmith])
    def deny_booking(self, request, pk=None):
        booking = self.get_object()
        user = request.user

        if user.role != 'locksmith':
            return Response({'error': 'Only locksmiths can deny bookings.'}, status=403)

        if booking.locksmith_status != 'PENDING':
            return Response({'error': 'Booking has already been responded to.'}, status=400)

        if booking.payment_status != 'paid':
            return Response({'error': 'Cannot deny booking. Payment is not completed.'}, status=400)

        booking.locksmith_status = 'DENIED'
        booking.status = 'Cancelled'
        booking.payment_status = 'refunded'
        booking.save()

        customer = booking.customer

        # Notify customer about denial
        customer_message = (
            f"Hello {customer.get_full_name()},\n"
            f"Your booking (ID: {booking.id}) has been denied by the locksmith.\n"
            f"A refund will be processed, and you may choose another service provider from LockQuick.\n"
            f"Visit https://lockquick.com.au/ to book again.\n"
            f"Thank you for choosing LockQuick."
        )
        send_sms(booking.customer_contact_number or customer.phone_number, customer_message)

        # TODO: Implement Stripe refund logic here

        return Response({'status': 'Booking denied and customer notified.'})

    
    @action(detail=True, methods=['post'], permission_classes=[IsLocksmith])
    def complete(self, request, pk=None):
        """
        Locksmith marks booking as completed and receives payment.
        Uses source_transaction for safe transfer tied to Stripe charge.
        """
        booking = self.get_object()
        locksmith_service = booking.locksmith_service
        locksmith = locksmith_service.locksmith

        # Pre-checks
        if booking.locksmith_status != "APPROVED":
            return Response({'error': 'Booking must be approved before completion.'}, status=400)

        if booking.status != "Scheduled":
            return Response({'error': 'Booking is not in a valid state to be completed'}, status=400)

        if not booking.payment_intent_id:
            return Response({'error': 'No PaymentIntent ID found.'}, status=400)

        if locksmith.user != request.user:
            return Response({'error': 'Permission denied'}, status=403)

        if not locksmith.stripe_account_id:
            return Response({'error': 'Locksmith does not have a Stripe account'}, status=400)

        try:
            # ✅ Safely retrieve the charge using PaymentIntent ID
            charges_list = stripe.Charge.list(payment_intent=booking.payment_intent_id)

            if not charges_list.data:
                return Response({'error': 'No charges found for this PaymentIntent.'}, status=400)

            charge_id = charges_list.data[0].id

            # Calculate transfer amount
            base_price = locksmith_service.custom_price or Decimal("0.00")
            number_of_keys = booking.number_of_keys or 0
            additional_key_price = locksmith_service.additional_key_price or Decimal("0.00")
            keys_total = additional_key_price * Decimal(number_of_keys)
            transfer_amount = base_price + keys_total
            transfer_amount_cents = int(transfer_amount * Decimal("100"))

            if transfer_amount_cents <= 0:
                return Response({'error': 'Transfer amount must be greater than zero.'}, status=400)

            # ✅ Create the transfer using source_transaction
            transfer = stripe.Transfer.create(
                amount=transfer_amount_cents,
                currency="aud",
                destination=locksmith.stripe_account_id,
                source_transaction=charge_id,
                transfer_group=f"booking_{booking.id}"
            )

            # ✅ Update booking record
            booking.status = "Completed"
            booking.payment_status = "paid"
            booking.charge_id = charge_id
            booking.transfer_status = "completed"
            booking.locksmith_transfer_amount = transfer_amount
            booking.save()

            return Response({
                'status': 'Booking completed and transfer created successfully.',
                'total_price': str(booking.total_price),
                'locksmith_transfer_amount': str(transfer_amount),
                'locksmith_charges': str(base_price),
                'additional_key_charges': str(keys_total),
                'charge_id': charge_id,
                'transfer_status': booking.transfer_status
            })

        except stripe.error.StripeError as e:
            return Response({'error': f'Stripe error: {str(e)}'}, status=400)

        except Exception as e:
            return Response({'error': f'Unexpected error while completing booking: {str(e)}'}, status=500)


    
    @action(detail=False, methods=["get"], permission_classes=[IsCustomer])
    def by_session(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response({"error": "Missing session_id"}, status=400)

        try:
            booking = Booking.objects.get(stripe_session_id=session_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=404)

        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    


    @action(detail=True, methods=['post'])
    def process_refund(self, request, pk=None):
        """Refund customer payment."""
        booking = self.get_object()

        if not booking.payment_intent_id:
            return Response({"error": "PaymentIntent ID is missing."}, status=400)

        try:
            refund = stripe.Refund.create(payment_intent=booking.payment_intent_id)
            booking.payment_status = "refunded"
            booking.save()

            return Response({"message": "Refund successful", "refund_id": refund.id})

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Customer cancels the booking."""
        booking = self.get_object()
        if booking.customer != request.user:
            return Response({'error': 'Permission denied'}, status=403)

        if booking.payment_status == "pending":
            try:
                stripe.PaymentIntent.cancel(booking.payment_intent_id)
            except stripe.error.StripeError:
                return Response({'error': 'Failed to cancel payment'}, status=400)

        booking.payment_status = "canceled"
        booking.save()
        return Response({'status': 'Booking canceled'})

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        """List bookings for the authenticated user."""
        user = request.user
        if user.role == "customer":
            bookings = Booking.objects.filter(customer=user,payment_status='paid')
        elif user.role == "locksmith":
            try:
                locksmith = Locksmith.objects.get(user=user)
                bookings = Booking.objects.filter(locksmith_service__locksmith=locksmith,
                payment_status='paid')
            except Locksmith.DoesNotExist:
                return Response({"error": "No locksmith profile found"}, status=400)
        elif user.role == "admin":
            bookings = Booking.objects.all()
        else:
            return Response({"error": "Unauthorized"}, status=403)

        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)
    
    
    
    @action(detail=False, methods=["get"], permission_classes=[IsAdmin])
    def admin_earnings_summary(self, request):
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        export_csv = request.GET.get("export") == "csv"

        bookings = Booking.objects.filter(status="Completed")

        if start_date:
            bookings = bookings.filter(scheduled_date__gte=start_date)
        if end_date:
            bookings = bookings.filter(scheduled_date__lte=end_date)

        total_customer_paid = sum(b.total_price or Decimal("0.00") for b in bookings)
        total_transferred_to_locksmiths = sum(b.locksmith_transfer_amount or Decimal("0.00") for b in bookings)
        admin_earnings = total_customer_paid - total_transferred_to_locksmiths

        if export_csv:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="earnings_summary.csv"'

            writer = csv.writer(response)
            writer.writerow(['Booking ID', 'Customer', 'Locksmith', 'Total Paid', 'Transferred', 'Transfer Status', 'Date'])

            for b in bookings:
                writer.writerow([
                    b.id,
                    b.customer.get_full_name() if b.customer else '',
                    b.locksmith_service.locksmith.user.get_full_name() if b.locksmith_service else '',
                    b.total_price,
                    b.locksmith_transfer_amount,
                    b.transfer_status,
                    b.scheduled_date.strftime('%Y-%m-%d %H:%M')
                ])

            writer.writerow([])
            writer.writerow(['Total Paid', 'Transferred to Locksmiths', 'Admin Earnings'])
            writer.writerow([total_customer_paid, total_transferred_to_locksmiths, admin_earnings])
            return response

        return Response({
            "total_customer_paid": float(total_customer_paid),
            "total_transferred_to_locksmiths": float(total_transferred_to_locksmiths),
            "admin_earnings": float(admin_earnings),
            "booking_count": bookings.count(),
            "start_date": start_date,
            "end_date": end_date
        })
    
    


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        print("❌ Webhook error:", str(e))
        return HttpResponse(status=400)

    print("✅ Event type:", event['type'])

    # ✅ Booking confirmation on successful payment
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session.get('id')
        print("🔎 Session ID:", session_id)

        try:
            booking = Booking.objects.get(stripe_session_id=session_id)

            if session.get('payment_status') == 'paid':
                booking.payment_intent_id = session.get('payment_intent')
                booking.payment_status = 'paid'
                booking.status = 'Scheduled'
                booking.save()

                customer = booking.customer
                locksmith = booking.locksmith_service.locksmith

                # Send SMS to customer
                customer_message = (
                    f"Hello {customer.get_full_name()},\n"
                    f"Your payment for the booking (ID: {booking.id}) is successful.\n"
                    f"Please wait for the locksmith to approve your request.\n"
                    f"You will be notified once it's approved or denied."
                )
                send_sms(booking.customer_contact_number or customer.phone_number, customer_message)

                # Notify locksmith
                locksmith_message = (
                    f"Hello {locksmith.user.get_full_name()},\n"
                    f"You have a new booking (ID: {booking.id}) from customer {customer.get_full_name()}.\n"
                    f"Service: {booking.locksmith_service.admin_service.name}\n"
                    f"Scheduled Date: {booking.scheduled_date.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Emergency Service: {'Yes' if booking.emergency else 'No'}\n"
                    f"Please approve or deny this booking."
                )
                send_sms(locksmith.contact_number, locksmith_message)

                print(f"✅ Booking {booking.id} updated and SMS sent.")

        except Booking.DoesNotExist:
            print(f"❌ Booking not found for session ID: {session_id}")
            return JsonResponse({"error": "Booking not found"}, status=404)

    # ✅ Update transfer status when funds are released
    elif event['type'] == 'transfer.paid':
        transfer = event['data']['object']
        charge_id = transfer.get('source_transaction')
        amount_cents = transfer.get('amount')

        print("🔄 Transfer Paid for Charge:", charge_id)

        try:
            booking = Booking.objects.get(charge_id=charge_id)

            booking.transfer_status = "completed"
            booking.locksmith_transfer_amount = Decimal(amount_cents) / 100
            booking.save()

            print(f"✅ Transfer recorded for booking {booking.id}")

        except Booking.DoesNotExist:
            print(f"⚠️ No booking found for charge ID: {charge_id}")

    return HttpResponse(status=200)




@api_view(['GET'])
def stripe_session_details(request):
    session_id = request.GET.get('session_id')
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return Response({
            "id": session.id,
            "payment_status": session.payment_status,
            "amount_total": session.amount_total
        })
    except stripe.error.StripeError as e:
        return Response({"error": str(e)}, status=400)






stripe.api_key = settings.STRIPE_SECRET_KEY

def get_mcc_code(request):
    try:
        # Retrieve account details
        account = stripe.Account.retrieve()
        mcc_code = account.get("business_profile", {}).get("mcc", "MCC not assigned")
        
        return JsonResponse({"mcc": mcc_code})
    
    except stripe.error.StripeError as e:
        return JsonResponse({"error": str(e)}, status=400)
    



class ContactMessageViewSet(viewsets.ModelViewSet):
    queryset = ContactMessage.objects.all().order_by('-created_at')
    serializer_class = ContactMessageSerializer

    def perform_create(self, serializer):
        instance = serializer.save()

        # Send auto-response email
        subject = "Thank you for contacting us!"
        message = f"Hello {instance.name},\n\nWe received your message: {instance.message}\n\nWe will get back to you soon!"
        send_mail(subject, message, 'your-email@example.com', [instance.email])
        
        
        
        
        
        
        
        
        
    
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from rest_framework import viewsets, status
from rest_framework.response import Response
import random
import pyotp
from rest_framework.permissions import AllowAny 
import qrcode
import base64
from io import BytesIO

User = get_user_model()

class ForgotPasswordViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for handling Forgot Password functionality.
    """
    queryset = User.objects.all()
    http_method_names = ['post']
    permission_classes = [AllowAny] # Allow only POST requests

    def create(self, request, *args, **kwargs):
        action = request.data.get('action')

        if action == 'forgot_password':
            return self.forgot_password(request)
        elif action == 'reset_password':
            return self.reset_password(request)
        else:
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

    def forgot_password(self, request):
        """
        Generates and sends OTP to the user's email for password reset.
        """
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        otp = str(random.randint(100000, 999999))  # Generate a 6-digit OTP
        user.otp_code = otp  # Store in otp_code field (not totp_secret)
        user.save()

        send_mail(
            'Password Reset OTP',
            f'Your OTP code is {otp}',
            'contact@lockquick.com.au',
            [email],
            fail_silently=False,
        )

        return Response({'message': 'OTP sent to your email', 'user_id': user.id}, status=status.HTTP_200_OK)

    def reset_password(self, request):
        
        email = request.data.get('email')
        otp = request.data.get('otp')
        new_password = request.data.get('new_password')

        if not (email and otp and new_password):
            return Response({'error': 'All fields are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        if user.otp_code != otp:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Reset Password
        user.set_password(new_password)
        user.otp_code = None  # Clear OTP after reset

        # ✅ Generate a new TOTP secret & update it in the database
        user.totp_secret = pyotp.random_base32()
        user.save()

        # ✅ Generate the provisioning URI (Google Authenticator)
        totp = pyotp.TOTP(user.totp_secret)
        qr_code_url = totp.provisioning_uri(name=user.email, issuer_name="LockQuick")

        # ✅ Generate QR Code Image (Base64)
        qr = qrcode.make(qr_code_url)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        return Response({
            'message': 'Password reset successful',
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'totp_enabled': True,
                'totp_secret': user.totp_secret,  # Send only if necessary
                'totp_qr_code': qr_base64,  # Base64-encoded QR code image
                'totp_qr_code_url': qr_code_url,  # URL for manual entry
            }
        }, status=status.HTTP_200_OK)
        
        
        
        
        
        
        
        
        
        
        
        
        
from dj_rest_auth.registration.views import SocialLoginView
from .serializers import CustomSocialLoginSerializer
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

class CustomGoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = "https://lockquick.com.au/accounts/google/login/callback/"
    serializer_class = CustomSocialLoginSerializer

class CustomFacebookLogin(SocialLoginView):
    serializer_class = CustomSocialLoginSerializer
    adapter_class = FacebookOAuth2Adapter
    
    
    
    
    
    
    
    
    
# import base64
# import hashlib
# import hmac
# import json

# from django.conf import settings
# from django.http import JsonResponse, HttpResponseBadRequest
# from django.views.decorators.csrf import csrf_exempt

# def base64_url_decode(input_str):
#     input_str += '=' * (-len(input_str) % 4)
#     return base64.urlsafe_b64decode(input_str.encode())

# @csrf_exempt
# def facebook_data_deletion(request):
#     if request.method == 'POST':
#         signed_request = request.POST.get('signed_request')
#         if not signed_request:
#             return HttpResponseBadRequest("Missing signed_request")

#         encoded_sig, payload = signed_request.split('.', 1)

#         # Decode data
#         sig = base64_url_decode(encoded_sig)
#         data = json.loads(base64_url_decode(payload))

#         # Verify the algorithm
#         if data.get('algorithm', '').upper() != 'HMAC-SHA256':
#             return HttpResponseBadRequest("Invalid algorithm")

#         # Validate signature
#         expected_sig = hmac.new(
#             settings.FACEBOOK_APP_SECRET.encode(),
#             msg=payload.encode(),
#             digestmod=hashlib.sha256
#         ).digest()

#         if not hmac.compare_digest(sig, expected_sig):
#             return HttpResponseBadRequest("Invalid signature")

#         fb_user_id = data.get('user_id')

#         # Delete user data from your database (example)
#         from api.models import User
#         User.objects.filter(facebook_id=fb_user_id).delete()

#         response = {
#             "url": "https://lockquick.com.au/deletion-confirmation/",
#             "confirmation_code": fb_user_id
#         }
#         return JsonResponse(response)

#     return HttpResponseBadRequest("Only POST allowed")







class GoogleLoginAPI(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    
    
    
class GoogleLoginWithRole(APIView):
    def post(self, request, *args, **kwargs):
        access_token = request.data.get("access_token")
        role = request.data.get("role")

        if not access_token:
            raise ValidationError("Access token is required.")
        
        if role not in ['customer', 'locksmith']:
            raise ValidationError("Invalid role. Role must be 'customer' or 'locksmith'.")
        
        # Call the existing logic for Google login, but include the role
        google_adapter = GoogleOAuth2Adapter()
        google_login = google_adapter.complete_login(request, access_token)
        
        # Pass the role through the sociallogin process
        google_login.user.role = role  # Assign role to user
        
        # Save the user and proceed
        google_login.save(request)
        
        # Respond with the user data and token
        return Response({
            "user": google_login.user.get_user_data(),
            "token": google_login.user.auth_token.key  # Assuming you are using token authentication
        })
        
        
        
        
        
        
# import firebase_admin
# from firebase_admin import credentials, auth
# from rest_framework.response import Response
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import AllowAny

# # Initialize Firebase Admin SDK
# cred = credentials.Certificate("C:/Users/Bornov Engineering/Desktop/back/locks/locksmith/secrets/lockquick-a63b9-firebase-adminsdk-fbsvc-678defaa16.json")
# if not firebase_admin._apps:
#     firebase_admin.initialize_app(cred)

# @api_view(['POST'])
# @permission_classes([AllowAny])
# def google_login(request):
#     # Get token from the request body
#     id_token = request.data.get('token')

#     if not id_token:
#         return Response({'error': 'Token required'}, status=400)

#     try:
#         # Verify Firebase token
#         decoded_token = auth.verify_id_token(id_token)
#         email = decoded_token['email']
#         username = decoded_token.get('name') or email.split("@")[0]
#         print("Decoded Token:", decoded_token)

#         # Here you can handle user creation or updates, etc.
#         return Response({'message': 'Token verified successfully', 'decoded_token': decoded_token})

#     except auth.ExpiredIdTokenError:
#         return Response({'error': 'Token expired'}, status=401)
#     except auth.RevokedIdTokenError:
#         return Response({'error': 'Token has been revoked'}, status=401)
#     except Exception as e:
#         return Response({'error': 'Invalid token', 'message': str(e)}, status=401)








# import firebase_admin
# from firebase_admin import credentials, auth
# from rest_framework.response import Response
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import AllowAny
# from django.contrib.auth import get_user_model
# from rest_framework_simplejwt.tokens import RefreshToken  # ✅ Use SimpleJWT

# # Initialize Firebase Admin SDK
# cred = credentials.Certificate("C:/Users/Bornov Engineering/Desktop/back/locks/locksmith/secrets/lockquick-a63b9-firebase-adminsdk-fbsvc-678defaa16.json")
# if not firebase_admin._apps:
#     firebase_admin.initialize_app(cred)

# User = get_user_model()

# @api_view(['POST'])
# @permission_classes([AllowAny])
# def google_login(request):
#     # Get the token and role from the request body
#     id_token = request.data.get('token')
#     role = request.data.get('role', 'customer')  # Default role is 'customer'

#     if not id_token:
#         return Response({'error': 'Token required'}, status=400)

#     try:
#         # Verify Firebase token
#         decoded_token = auth.verify_id_token(id_token)
#         email = decoded_token['email']
#         username = decoded_token.get('name') or email.split("@")[0]

#         # Check if the user exists or create a new one
#         user, created = User.objects.get_or_create(email=email, defaults={'username': username})

#         # If user is newly created or the role needs to be updated, set the role
#         if created or user.role != role:
#             user.role = role
#             user.save()

#         # ✅ Generate tokens using SimpleJWT
#         refresh = RefreshToken.for_user(user)
#         access_token = str(refresh.access_token)
#         refresh_token = str(refresh)

#         return Response({
#             'message': 'Token verified successfully',
#             'user': {
#                 'id': user.id,
#                 'username': user.username,
#                 'email': user.email,
#                 'role': user.role
#             },
#             'access_token': access_token,
#             'refresh_token': refresh_token
#         })

#     except auth.ExpiredIdTokenError:
#         return Response({'error': 'Token expired'}, status=401)
#     except auth.RevokedIdTokenError:
#         return Response({'error': 'Token has been revoked'}, status=401)
#     except Exception as e:
#         return Response({'error': 'Invalid token', 'message': str(e)}, status=401)






import logging
import firebase_admin
from firebase_admin import credentials, auth
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

# Initialize logging
logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
cred = credentials.Certificate("/home/ubuntu/lockquick/locksmith/secrets/lockquick-6f1b8-firebase-adminsdk-fbsvc-55d681f13b.json")
# cred = credentials.Certificate("C:/Users/Bornov Engineering/Desktop/back/locks/locksmith/secrets/lockquick-6f1b8-firebase-adminsdk-fbsvc-55d681f13b.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

VALID_ROLES = ['customer', 'admin', 'locksmith']  # Define allowed roles

User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    # Log incoming request
    logger.info(f"Received request: {request.data}")

    id_token = request.data.get('token')
    role = request.data.get('role', 'customer')  # Default role is 'customer'

    # Check if the role is valid before proceeding
    if role not in VALID_ROLES:
        logger.error(f"Invalid role: {role}")
        return Response({'error': 'Invalid role'}, status=400)

    if not id_token:
        return Response({'error': 'Token required'}, status=400)

    try:
        # Verify Firebase token
        decoded_token = auth.verify_id_token(id_token)
        logger.info(f"Decoded token: {decoded_token}")

        email = decoded_token['email']
        username = decoded_token.get('name') or email.split("@")[0]

        # Check if the user exists or create a new one
        user, created = User.objects.get_or_create(email=email, defaults={'username': username})

        # If user is newly created or the role needs to be updated, set the role
        if created or user.role != role:
            user.role = role
            user.save()

        # Generate tokens using SimpleJWT
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        return Response({
            'message': 'Token verified successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            },
            'access_token': access_token,
            'refresh_token': refresh_token
        })

    except auth.ExpiredIdTokenError as e:
        logger.error(f"Token expired: {e}")
        return Response({'error': 'Token expired'}, status=401)
    except auth.RevokedIdTokenError as e:
        logger.error(f"Token has been revoked: {e}")
        return Response({'error': 'Token has been revoked'}, status=401)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return Response({'error': 'Invalid token', 'message': str(e)}, status=401)





# import logging
# import firebase_admin
# from firebase_admin import credentials, auth
# from rest_framework.response import Response
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import AllowAny
# from django.contrib.auth import get_user_model
# from rest_framework_simplejwt.tokens import RefreshToken
# import time

# # Initialize logging
# logger = logging.getLogger(__name__)

# # Initialize Firebase Admin SDK
# cred = credentials.Certificate("C:/Users/Bornov Engineering/Desktop/back/locks/locksmith/secrets/lockquick-a63b9-firebase-adminsdk-fbsvc-678defaa16.json")
# if not firebase_admin._apps:
#     firebase_admin.initialize_app(cred)

# VALID_ROLES = ['customer', 'admin', 'locksmith']  

# User = get_user_model()

# import time

# GRACE_PERIOD = 300  # 5 minutes grace period for clock discrepancy

# @api_view(['POST'])
# @permission_classes([AllowAny])
# def google_login(request):
#     # Log incoming request
#     logger.info(f"Received request: {request.data}")
    
#     # Retrieve the token and role from the request data
#     id_token = request.data.get('token')
#     role = request.data.get('role', 'customer')  # Default role is 'customer'

#     if not id_token:
#         return Response({'error': 'Token required'}, status=400)

#     # Validate the role
#     if role not in VALID_ROLES:
#         return Response({'error': 'Invalid role'}, status=400)

#     try:
#         # Get the current time (in seconds since epoch)
#         current_time = time.time()

#         # Verify Firebase token
#         decoded_token = auth.verify_id_token(id_token, check_revoked=True)
#         logger.info(f"Decoded token: {decoded_token}")

#         # Check if the token's 'iat' (issued at) claim is too far in the past
#         if decoded_token['iat'] > current_time + GRACE_PERIOD:
#             raise auth.ExpiredIdTokenError("Token is used too early")

#         email = decoded_token['email']
#         username = decoded_token.get('name') or email.split("@")[0]

#         # Check if the user exists or create a new one
#         user, created = User.objects.get_or_create(email=email, defaults={'username': username})

#         # If user is newly created or the role needs to be updated, set the role
#         if created or user.role != role:
#             user.role = role
#             user.save()

#         # Generate tokens using SimpleJWT
#         refresh = RefreshToken.for_user(user)
#         access_token = str(refresh.access_token)
#         refresh_token = str(refresh)

#         return Response({
#             'message': 'Token verified successfully',
#             'user': {
#                 'id': user.id,
#                 'username': user.username,
#                 'email': user.email,
#                 'role': user.role
#             },
#             'access_token': access_token,
#             'refresh_token': refresh_token
#         })

#     except auth.ExpiredIdTokenError as e:
#         logger.error(f"Token expired or used too early: {e}")
#         return Response({'error': 'Token expired or used too early'}, status=401)
#     except auth.RevokedIdTokenError:
#         logger.error('Token has been revoked')
#         return Response({'error': 'Token has been revoked'}, status=401)
#     except Exception as e:
#         logger.error(f"Error: {str(e)}")
#         return Response({'error': 'Invalid token', 'message': str(e)}, status=401)





import requests
from django.http import JsonResponse
from django.conf import settings

def get_address_suggestions(request):
    query = request.GET.get('query', '')
    api_key = settings.GOOGLE_MAPS_API_KEY
    url = f'https://maps.googleapis.com/maps/api/place/autocomplete/json?input={query}&key={api_key}'

    response = requests.get(url)
    suggestions = response.json()

    return JsonResponse(suggestions)






# @csrf_exempt
# def stripe_webhook(request):
#     payload = request.body
#     print("📦 Raw Payload:", payload)  # Debug

#     sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
#     webhook_secret = settings.STRIPE_WEBHOOK_SECRET

#     try:
#         event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
#     except Exception as e:
#         print("❌ Webhook error:", str(e))
#         return HttpResponse(status=400)

#     print("✅ Event type:", event['type'])

#     if event['type'] == 'checkout.session.completed':
#         session = event['data']['object']
#         session_id = session.get('id')
#         print("🔎 Session ID:", session_id)

#         try:
#             booking = Booking.objects.get(stripe_session_id=session_id)
#             booking.payment_status = 'paid'
#             booking.payment_intent_id = session.get('payment_intent')
#             booking.save()
#             print(f"✅ Booking {booking.id} marked as paid via webhook.")
#         except Booking.DoesNotExist:
#             print(f"❌ Booking not found for session ID: {session_id}")
#             return JsonResponse({"error": "Booking not found"}, status=404)

#     return HttpResponse(status=200)



    
    
    
    
    
    
# from rest_framework.decorators import api_view, permission_classes, authentication_classes
# from rest_framework.permissions import AllowAny
# from rest_framework.authentication import BasicAuthentication
    
    
    
# @api_view(['POST'])
# @permission_classes([AllowAny])
# @authentication_classes([]) 
# def complete_booking_public(request, booking_id):
#     """
#     Public (unauthenticated) version of the booking completion API.
#     ⚠️ Use only for testing or limited use — not secure for production.
#     """
#     try:
#         booking = Booking.objects.get(id=booking_id)
#     except Booking.DoesNotExist:
#         return Response({'error': 'Booking not found'}, status=404)

#     locksmith_service = booking.locksmith_service
#     locksmith = locksmith_service.locksmith

#     if booking.locksmith_status != "APPROVED":
#         return Response({'error': 'Booking must be approved before completion.'}, status=400)

#     if booking.status != "Scheduled":
#         return Response({'error': 'Booking is not in a valid state to be completed'}, status=400)

#     if not booking.payment_intent_id:
#         return Response({'error': 'No PaymentIntent ID found. Ensure payment is completed.'}, status=400)

#     if not locksmith.stripe_account_id:
#         return Response({'error': 'Locksmith does not have a Stripe account'}, status=400)

#     try:
#         payment_intent = stripe.PaymentIntent.retrieve(booking.payment_intent_id)

#         if payment_intent.status == "succeeded":
#             admin_settings = AdminSettings.objects.first()
#             commission_amount = admin_settings.commission_amount or Decimal("0.00")
#             percentage = admin_settings.percentage or Decimal("0.00")
#             gst_percentage = admin_settings.gst_percentage or Decimal("0.00")

#             base_price = locksmith_service.custom_price or Decimal("0.00")
#             number_of_keys = booking.number_of_keys or 0
#             additional_key_price = locksmith_service.additional_key_price or Decimal("0.00")
#             keys_total = additional_key_price * Decimal(number_of_keys)

#             subtotal = base_price + keys_total
#             percentage_amount = (subtotal * percentage) / Decimal("100")
#             platform_income = commission_amount + percentage_amount
#             gst_amount = (platform_income * gst_percentage) / Decimal("100")
#             total_price = booking.total_price or Decimal("0.00")
#             transfer_amount = base_price + keys_total

#             if transfer_amount <= 0:
#                 return Response({'error': 'Transfer amount is zero or negative.'}, status=400)

#             transfer_amount_cents = int(transfer_amount * Decimal('100'))

#             stripe.Transfer.create(
#                 amount=transfer_amount_cents,
#                 currency="aud",
#                 destination=locksmith.stripe_account_id,
#                 transfer_group=f"booking_{booking.id}"
#             )

#             booking.status = "Completed"
#             booking.payment_status = "paid"
#             booking.save()

#             return Response({
#                 'status': 'Booking completed and payment transferred to locksmith',
#                 'total_price': str(total_price),
#                 'locksmith_transfer_amount': str(transfer_amount),
#                 'locksmith_charges': str(base_price),
#                 'additional_key_charges': str(keys_total),
#                 'platform_charges': str(commission_amount),
#                 'service_charges': str(percentage_amount),
#                 'gst': str(gst_amount),
#                 'platform_income': str(platform_income),
#             })

#         else:
#             return Response({'error': f'PaymentIntent not succeeded. Status: {payment_intent.status}'}, status=400)

#     except stripe.error.StripeError as e:
#         return Response({'error': str(e)}, status=400)











# phase 2

from .models import WebsiteContent
from .serializers import WebsiteContentSerializer
from django.core.mail import EmailMessage



class WebsiteContentViewSet(viewsets.ModelViewSet):
    queryset = WebsiteContent.objects.all()
    serializer_class = WebsiteContentSerializer

    def get_permissions(self):
        # Allow anyone to GET (safe methods), others require admin
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [IsAdmin()]

    def get_queryset(self):
        section = self.request.query_params.get('section')
        base_qs = WebsiteContent.objects.all()  # freshly evaluated
        if section:
            return base_qs.filter(section=section)
        return base_qs






















from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone

from .models import User, Locksmith, Customer , SuggestedService , CCTVTechnicianPreRegistration
from .serializers import UserCreateSerializer , SuggestedServiceSerializer ,CCTVTechnicianPreRegistrationSerializer
from .utils import send_email_otp
from .utils import verify_user_otp , send_password_reset_otp



class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # ✅ Set role and create Customer profile if needed
            if user.role == "customer":
                Customer.objects.create(
                    user=user,
                    latitude=request.data.get("latitude"),
                    longitude=request.data.get("longitude"),
                    address=request.data.get("address", ""),
                    contact_number=request.data.get("contact_number", "")
                )

            # ✅ Do NOT create Locksmith profile, just set the role
            elif user.role == "locksmith":
                pass  # Just keep the role in the User model

            # ✅ Always send TOTP details
            totp_details = serializer.get_totp_details(user)

            # ✅ Always send Email OTP
            send_email_otp(user)

            return Response({
                "message": "Registration successful",
                "user_id": user.id,
                "email": user.email,
                "role": user.role,
                "totp_secret": totp_details["totp_secret"],
                "totp_qr_code": totp_details["totp_qr_code"],
                "qr_code_url": totp_details["qr_code_url"],
                "info": "TOTP QR Code and Email OTP sent. Please verify either one.",
                "next_step": "verify_otp"
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    
    
    
User = get_user_model()

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        role = request.data.get('role')
        otp_code = request.data.get('otp_code')

        if not username or not role or not otp_code:
            return Response({"error": "Username, role, and OTP code are required"}, status=400)

        try:
            user = User.objects.get(username=username, role=role)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        valid, method = verify_user_otp(user, otp_code)

        if not valid:
            if method == "expired":
                return Response({"error": "OTP has expired"}, status=400)
            return Response({"error": "Invalid OTP code"}, status=400)

        # ✅ OTP verified – issue JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            "message": f"OTP verified using {method.upper()}",
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=200)
  

class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        role = request.data.get('role')

        if not username or not role:
            return Response({"error": "Username and role are required"}, status=400)

        try:
            user = User.objects.get(username=username, role=role)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        try:
            send_email_otp(user)
            return Response({
                "message": "A new email OTP has been sent to your email address."
            }, status=200)
        except Exception as e:
            return Response({
                "error": f"Failed to send OTP. Reason: {str(e)}"
            }, status=500)
        
        


class LoginStepOneView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        expected_role = request.data.get("role")

        if not expected_role:
            return Response({'error': 'Role is required'}, status=400)

        user = authenticate(username=username, password=password)
        if not user:
            return Response({'error': 'Invalid credentials'}, status=401)

        if user.role != expected_role:
            return Response({'error': f'Invalid role. You are registered as {user.role}.'}, status=403)

        send_email_otp(user)

        return Response({
            'message': 'Step 1 successful. OTP sent via email. You can also use Google Authenticator.',
            'user_id': user.id,
            'role': user.role,
            'has_totp': bool(user.totp_secret),
        }, status=200)





class LoginStepTwoView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        otp_code = request.data.get("otp_code")
        role = request.data.get("role")

        if not username or not otp_code or not role:
            return Response({"error": "Username, OTP, and Role are required"}, status=400)

        try:
            user = User.objects.get(username=username, role=role)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        valid, method = verify_user_otp(user, otp_code)

        if not valid:
            return Response({
                "error": "OTP expired" if method == "expired" else "Invalid OTP code"
            }, status=400)

        return self.login_success(user)

    def login_success(self, user):
        refresh = RefreshToken.for_user(user)

        data = {
            "message": "Login successful",
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

        # Locksmith extra fields
        if user.role == "locksmith":
            locksmith = getattr(user, "locksmith", None)
            if locksmith:
                data.update({
                    "is_verified": locksmith.is_verified,
                    "is_approved": locksmith.is_approved,
                })

        return Response(data, status=200)
    
 
 
 
 
 
class ForgotPasswordRequestView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required"}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "No account found with this email"}, status=404)

        send_password_reset_otp(user)
        return Response({"message": "OTP sent to your email"}, status=200)
    
    
    
    
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        new_password = request.data.get("new_password")

        if not email or not otp or not new_password:
            return Response({"error": "Email, OTP, and new password are required"}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Invalid email"}, status=404)

        if user.otp_code != otp:
            return Response({"error": "Invalid OTP"}, status=400)

        if timezone.now() > user.otp_expiry:
            return Response({"error": "OTP has expired"}, status=400)

        user.set_password(new_password)
        user.otp_code = None
        user.otp_expiry = None
        user.save()

        return Response({"message": "Password reset successful"}, status=200)
 
 
 
 
 
class CCTVTechnicianPreRegistrationViewSet(viewsets.ModelViewSet):
    queryset = CCTVTechnicianPreRegistration.objects.all()
    serializer_class = CCTVTechnicianPreRegistrationSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [AllowAny()]  # Public access for POST
        return [IsAdmin()]  # Authentication required for GET, PUT, DELETE, PATCH
 
 
 
 
 
 
    
    
    
User = get_user_model()
logger = logging.getLogger(__name__)

class SuggestedServiceViewSet(viewsets.ModelViewSet):
    queryset = SuggestedService.objects.all()
    serializer_class = SuggestedServiceSerializer

    def perform_create(self, serializer):
        suggestion = serializer.save(suggested_by=self.request.user)

        # Format posted data
        posted_data = "\n".join([
            f"{key}: {value}"
            for key, value in self.request.data.items()
            if key != "car_key_details"
        ])

        # Format car key details if present
        car_keys_data = ""
        if "car_key_details" in self.request.data and self.request.data["car_key_details"]:
            car_keys = self.request.data["car_key_details"]
            try:
                if isinstance(car_keys, str):
                    car_keys = json.loads(car_keys)
                car_keys_data = "\n\nCar Key Details:\n"
                for idx, key in enumerate(car_keys, start=1):
                    car_keys_data += (
                        f"\nKey {idx}:\n"
                        f"Manufacturer: {key.get('manufacturer')}\n"
                        f"Model: {key.get('model')}\n"
                        f"Year From: {key.get('year_from')}\n"
                        f"Year To: {key.get('year_to')}\n"
                        f"Number of Buttons: {key.get('number_of_buttons')}\n"
                    )
            except Exception as e:
                car_keys_data += "\nError reading car key details.\n"

        message_body = (
            f"🔔 Locksmith {self.request.user.username} suggested a new service:\n\n"
            f"{posted_data}"
            f"{car_keys_data}"
        )

        try:
            send_mail(
                subject="🔔 New Service Suggestion from Locksmith",
                message=message_body,
                from_email="contact@lockquick.com.au",
                recipient_list=["contact@lockquick.com.au"],
                fail_silently=True
            )
        except Exception as e:
            logger.error(f"[EMAIL ERROR] Failed to send suggestion email to admin: {e}")

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def confirm_and_add(self, request, pk=None):
        suggestion = get_object_or_404(SuggestedService, pk=pk)

        if AdminService.objects.filter(name__iexact=suggestion.name, service_type=suggestion.service_type).exists():
            return Response({"error": "This service already exists."}, status=400)

        serializer = self.get_serializer(suggestion, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        suggestion = serializer.save(status='approved')

        name = serializer.validated_data.get('name', suggestion.name)
        service_type = serializer.validated_data.get('service_type', suggestion.service_type)

        new_service = AdminService.objects.create(
            name=name,
            service_type=service_type
        )
        logger.info(f"[SERVICE CREATE] AdminService created: {new_service}")

        # Create all CarKeyDetails if applicable
        car_key_objs = []
        if service_type == 'automotive' and suggestion.car_key_details:
            for key_data in suggestion.car_key_details:
                try:
                    created_key = CarKeyDetails.objects.create(
                        manufacturer=key_data.get('manufacturer'),
                        model=key_data.get('model'),
                        year_from=key_data.get('year_from'),
                        year_to=key_data.get('year_to'),
                        number_of_buttons=key_data.get('number_of_buttons')
                    )
                    car_key_objs.append(created_key)
                    logger.info(f"[CAR KEY CREATE] {created_key}")
                except Exception as e:
                    logger.error(f"[CAR KEY ERROR] Failed to create key: {e}")

        # Create locksmith service(s)
        try:
            locksmith = Locksmith.objects.get(user=suggestion.suggested_by)

            if car_key_objs:
                for key_obj in car_key_objs:
                    LocksmithServices.objects.create(
                        locksmith=locksmith,
                        admin_service=new_service,
                        custom_price=suggestion.price,
                        total_price=suggestion.price,
                        service_type=service_type,
                        approved=True,
                        additional_key_price=suggestion.additional_key_price,
                        car_key_details=key_obj
                    )
                    logger.info(f"[LOCKSMITH SERVICE CREATED] With car key: {key_obj}")
            else:
                LocksmithServices.objects.create(
                    locksmith=locksmith,
                    admin_service=new_service,
                    custom_price=suggestion.price,
                    total_price=suggestion.price,
                    service_type=service_type,
                    approved=True,
                    additional_key_price=suggestion.additional_key_price
                )
                logger.info(f"[LOCKSMITH SERVICE CREATED] Without car key")

        except Locksmith.DoesNotExist:
            logger.warning("[LOCKSMITH MISSING] No locksmith found for suggesting user.")

        # Notify the suggester
        if suggestion.suggested_by.email:
            try:
                EmailMessage(
                    subject="✅ Your Service Suggestion Approved",
                    body=(
                        f"Hi {suggestion.suggested_by.username},\n\n"
                        f"Your suggested service '{name}' has been approved and added to the system.\n"
                        f"Thank you for contributing!\n\n"
                        f"— Team LockQuick"
                    ),
                    from_email="contact@lockquick.com.au",
                    to=[suggestion.suggested_by.email]
                ).send(fail_silently=False)
                logger.info(f"[EMAIL] Sent approval to {suggestion.suggested_by.email}")
            except Exception as e:
                logger.error(f"[EMAIL ERROR] Could not notify suggester: {e}")

        # Notify all other locksmiths one-by-one
        # all_locksmiths = User.objects.filter(role='locksmith').exclude(id=suggestion.suggested_by.id)
        # logger.info(f"[EMAIL DEBUG] Total locksmiths to notify: {all_locksmiths.count()}")

        # for user in all_locksmiths:
        #     if user.email:
        #         try:
        #             EmailMessage(
        #                 subject=f"🆕 New Service Available: {name}",
        #                 body=(
        #                     f"Hi {user.username},\n\n"
        #                     f"A new service '{name}' has just been approved by admin and is now available in your dashboard.\n\n"
        #                     f"Log in to your dashboard to start offering this service.\n\n"
        #                     f"— Team LockQuick"
        #                 ),
        #                 from_email="contact@lockquick.com.au",
        #                 to=[user.email]
        #             ).send(fail_silently=False)
        #             logger.info(f"[EMAIL SENT] Notification sent to {user.email}")
        #         except Exception as e:
        #             logger.error(f"[EMAIL ERROR] Failed to send to {user.email}: {str(e)}")
        #     else:
        #         logger.warning(f"[EMAIL DEBUG] Skipped {user.username} — no email.")

        return Response({"detail": "Service approved and added successfully."})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject_suggestion(self, request, pk=None):
        suggestion = get_object_or_404(SuggestedService, pk=pk)
        suggestion.status = 'rejected'
        suggestion.save()

        # Optional rejection email
        if suggestion.suggested_by.email:
            try:
                EmailMessage(
                    subject="❌ Your Service Suggestion Was Rejected",
                    body=(
                        f"Hi {suggestion.suggested_by.username},\n\n"
                        f"Your suggested service '{suggestion.name}' was reviewed but not approved at this time.\n\n"
                        f"— Team LockQuick"
                    ),
                    from_email="contact@lockquick.com.au",
                    to=[suggestion.suggested_by.email]
                ).send(fail_silently=True)
            except Exception as e:
                logger.error(f"[EMAIL ERROR] Failed to notify rejection: {e}")

        return Response({"detail": "Suggestion rejected."})