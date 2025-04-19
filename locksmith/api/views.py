from rest_framework import viewsets, permissions
from .permissions import IsAdmin
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

            # Generate TOTP details for Locksmith
            totp_details = serializer.get_totp_details(user)

            return Response({
                'message': 'Locksmith registered successfully. Please complete your profile.',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'totp_enabled': user.totp_enabled,
                    'totp_secret': totp_details["totp_secret"],  # TOTP Key in Response
                    'totp_qr_code': totp_details["totp_qr_code"],  # Base64 QR Code
                    'totp_qr_code_url': totp_details["qr_code_url"],  # QR Image URL
                },
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
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
    
    
    
class LocksmithProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Create a new locksmith profile for the logged-in user.
        """
        user = request.user

        # Ensure the user is a locksmith
        if user.role != 'locksmith':
            return Response({"error": "Unauthorized. Only locksmiths can create profiles."}, status=status.HTTP_403_FORBIDDEN)

        # Check if the locksmith profile already exists
        if hasattr(user, 'locksmith'):
            return Response({"error": "Profile already exists."}, status=status.HTTP_400_BAD_REQUEST)

        # Create a new locksmith profile
        serializer = LocksmithSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=user)
            return Response({"message": "Profile created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """
        Update an existing locksmith profile.
        """
        user = request.user

        # Ensure the locksmith profile exists
        try:
            locksmith = user.locksmith
        except Locksmith.DoesNotExist:
            return Response({"error": "Locksmith profile not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = LocksmithSerializer(locksmith, data=request.data, partial=True)
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



# Custom Permissions
class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'admin'  # Adjust role check as per your user model

class IsLocksmith(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'locksmith'  # Adjust role check for locksmiths

class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'customer'  # Adjust role check for customers
    
    
class IsAdminOrCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ['admin', 'customer']
    
    
    
class IsAdminOrLocksmith(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ['admin', 'locksmith']

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
    permission_classes = [IsAdmin]  # Only Admin can manage car key details



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
        """Get all approved locksmith services, optionally filtered by service type and sorted by distance."""

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
            service_data.pop("custom_price", None)  # Remove custom_price from response

            # Ensure car_key_details appears only once
            car_key_details = service_data.pop("car_key_details", None)

            locksmith_services_with_distance.append({
                "locksmith": locksmith.user.username,
                "latitude": locksmith.latitude,
                "longitude": locksmith.longitude,
                "distance_km": round(distance_km, 2),
                "service": service_data,
                "car_key_details": car_key_details  # Only include car_key_details once
            })

        # Sort by nearest distance
        locksmith_services_with_distance.sort(key=lambda x: x["distance_km"])

        return Response(locksmith_services_with_distance)


    
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def available_services(self, request):
        """
        Get all services added by the admin so the logged-in locksmith can choose.
        """
        services = AdminService.objects.all()
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

    
    def perform_create(self, serializer):
        """Automatically assign the logged-in locksmith and calculate total price."""
        user = self.request.user

        # Ensure user has an associated Locksmith account
        if not hasattr(user, "locksmith"):
            raise serializers.ValidationError({"error": "User is not associated with a locksmith account."})

        locksmith = user.locksmith  # Now safe to access

        # Get admin commission settings
        admin_settings = AdminSettings.objects.first()
        if not admin_settings:
            raise serializers.ValidationError({"error": "Admin settings not configured."})

        # Fetch commission settings
        commission_amount = admin_settings.commission_amount if admin_settings else Decimal("0")
        percentage = admin_settings.percentage if admin_settings else Decimal("0")

        # Convert custom_price to Decimal
        custom_price = serializer.validated_data.get("custom_price", 0)
        custom_price = Decimal(str(custom_price))

        # Calculate percentage amount
        percentage_amount = (custom_price * percentage) / Decimal("100")
        total_price = custom_price + percentage_amount + commission_amount  # ✅ Correct formula

        # Handle Car Key Details for Automotive Services
        service_type = serializer.validated_data.get("service_type", "residential")
        car_key_details_data = self.request.data.get("car_key_details", None)

        if service_type == "automotive":
            if not car_key_details_data or not isinstance(car_key_details_data, dict):
                raise serializers.ValidationError({"error": "Car key details must be provided as a dictionary for automotive services."})

            # Create a CarKeyDetails instance with extracted dictionary values
            car_key_details = CarKeyDetails.objects.create(
                manufacturer=car_key_details_data.get("manufacturer"),
                model=car_key_details_data.get("model"),
                year=car_key_details_data.get("year"),
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
    permission_classes = [IsAuthenticated]
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
            'site_url': "http://127.0.0.1:8000/dashboard",  # Update with live URL
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
            'support_email': "support@lockquick.com.au"  # Replace with your support email
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
            refresh_url="http://localhost:8000/reauth",
            return_url="http://localhost:8000/dashboard",
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
        
      
        

    # Twilio Credentials (Replace with actual credentials)
TWILIO_ACCOUNT_SID = "ACba1e3f20eb7083c73471a9e87c04802c"
TWILIO_AUTH_TOKEN = "ca2a6daa04eed144e8bb9af1269a265e"
TWILIO_PHONE_NUMBER = "+12233572123"

def call_locksmith(locksmith_phone, locksmith_name, booking_id):
    """Function to call the locksmith after successful payment."""
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    message = f"Hello {locksmith_name}, you have received a new booking. Booking ID: {booking_id}. Please check your dashboard for details."
    
    call = client.calls.create(
        twiml=f'<Response><Say>{message}</Say></Response>',
        to=locksmith_phone,
        from_=TWILIO_PHONE_NUMBER
    )
    
    print(f"📞 Call triggered to Locksmith {locksmith_name} (Phone: {locksmith_phone}) - Call SID: {call.sid}")
    return call.sid
class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling bookings, payments, refunds, and status updates.
    """
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated] 
    
    def get_queryset(self):
        """Filter bookings based on logged-in user role."""
        user = self.request.user  

        if user.role == "customer":
            return Booking.objects.filter(customer=user)

        elif user.role == "locksmith":
            try:
                locksmith = Locksmith.objects.get(user=user)  
                return Booking.objects.filter(locksmith_service__locksmith=locksmith)  
            except Locksmith.DoesNotExist:
                return Booking.objects.none()  

        elif user.role == "admin":
            return Booking.objects.all()  

        return Booking.objects.none() 
        
    def perform_create(self, serializer):
        """
        Assign the authenticated user as the customer before saving.
        """
        user = self.request.user

        if not user.is_authenticated:
            raise serializers.ValidationError({"error": "User must be authenticated to create a booking."})

        if user.role != "customer":
            raise serializers.ValidationError({"error": "Only customers can create bookings."})

        serializer.save(customer=user)
        
        
        

    
    @action(detail=True, methods=['post'])
    def process_payment(self, request, pk=None):
        booking = self.get_object()
        locksmith_service = booking.locksmith_service  
        total_price = locksmith_service.total_price  

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card", "afterpay_clearpay", "klarna", "zip"],
                line_items=[{
                    'price_data': {
                        'currency': 'aud',
                        'product_data': {'name': locksmith_service.admin_service.name},
                        'unit_amount': int(total_price * 100),  # Convert to cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url="https://yourwebsite.com/payment-success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="https://yourwebsite.com/payment-cancel",
            )

            # 🔹 Save Stripe Session ID in Booking
            booking.stripe_session_id = checkout_session.id
            booking.payment_status = "pending"
            booking.save()

            print(f"✅ Saved Booking {booking.id} with Stripe Session ID: {checkout_session.id}")

            return Response({'checkout_url': checkout_session.url})

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)
    
    @action(detail=True, methods=['post'])
    def complete_payment(self, request, pk=None):
        """Handles payment completion and triggers a call to the locksmith."""
        booking = self.get_object()
        
        # Ensure payment was made
        if not booking.payment_intent_id:
            return Response({"error": "No PaymentIntent ID found. Ensure payment is completed."}, status=400)

        try:
            # Retrieve PaymentIntent
            payment_intent = stripe.PaymentIntent.retrieve(booking.payment_intent_id)

            if payment_intent.status == "succeeded":
                booking.payment_status = "paid"
                booking.status = "Scheduled"
                booking.save()
                
                # 🔹 Trigger a call to the locksmith
                locksmith = booking.locksmith_service.locksmith
                call_locksmith(locksmith.contact_number, locksmith.user.get_full_name(), booking.id)

                return Response({
                    "status": "Payment successful. Booking confirmed.",
                    "message": "Locksmith has been notified via an automated call."
                })

            return Response({"error": "Payment not completed."}, status=400)

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)
        

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Locksmith marks booking as completed and receives payment"""
        booking = self.get_object()

        # ✅ Ensure booking is scheduled
        if booking.status != "Scheduled":
            return Response({'error': 'Booking is not in a valid state to be completed'}, status=400)

        # ✅ Ensure payment exists
        if not booking.payment_intent_id:
            return Response({'error': 'No PaymentIntent ID found. Ensure payment is completed.'}, status=400)

        # ✅ Ensure locksmith is correct
        locksmith = booking.locksmith_service.locksmith
        if locksmith.user != request.user:
            return Response({'error': 'Permission denied'}, status=403)

        # ✅ Ensure locksmith has Stripe account
        if not locksmith.stripe_account_id:
            return Response({'error': 'Locksmith does not have a Stripe account'}, status=400)

        try:
            # ✅ Retrieve PaymentIntent
            payment_intent = stripe.PaymentIntent.retrieve(booking.payment_intent_id)

            # ✅ If payment is already captured, transfer funds
            if payment_intent.status == "succeeded":
                total_price = booking.locksmith_service.total_price
                custom_price = booking.locksmith_service.custom_price

                # ✅ Deduction Calculation
                deduct_amount = total_price - custom_price
                transfer_amount = custom_price  # Only sending locksmith's custom price

                # ✅ Convert to cents
                transfer_amount_cents = int(transfer_amount * 100)

                # ✅ Transfer money to locksmith
                transfer = stripe.Transfer.create(
                    amount=transfer_amount_cents,
                    currency="usd",
                    destination=locksmith.stripe_account_id,
                    transfer_group=f"booking_{booking.id}"
                )

                # ✅ Mark booking as completed
                booking.status = "Completed"
                booking.payment_status = "paid"
                booking.save()

                return Response({
                    'status': 'Booking completed and payment transferred to locksmith',
                    'transfer_amount': transfer_amount,
                    'deducted_amount': deduct_amount
                })
                

            else:
                return Response({'error': f'Invalid PaymentIntent status: {payment_intent.status}'}, status=400)

        except stripe.error.StripeError as e:
            return Response({'error': str(e)}, status=400)




    @action(detail=True, methods=['post'])
    def process_refund(self, request, pk=None):
        """
        ✅ Refund customer payment.
        """
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
        """
        ✅ Customer cancels the booking.
        """
        booking = self.get_object()
        if booking.customer != request.user:
            return Response({'error': 'Permission denied'}, status=403)
        
        if booking.payment_status == "pending":
            try:
                # ✅ Cancel Stripe Payment Intent if funds are held
                stripe.PaymentIntent.cancel(booking.payment_intent_id)
            except stripe.error.StripeError:
                return Response({'error': 'Failed to cancel payment'}, status=400)

        booking.payment_status = "canceled"
        booking.save()
        return Response({'status': 'Booking canceled'})

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        """
        ✅ List bookings for the authenticated user.
        """
        user = request.user
        if user.role == "customer":
            bookings = Booking.objects.filter(customer=user)
        elif user.role == "locksmith":
            try:
                locksmith = Locksmith.objects.get(user=user)
                bookings = Booking.objects.filter(locksmith_service__locksmith=locksmith)
            except Locksmith.DoesNotExist:
                return Response({"error": "No locksmith profile found"}, status=400)
        elif user.role == "admin":
            bookings = Booking.objects.all()
        else:
            return Response({"error": "Unauthorized"}, status=403)

        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)
    
    
    
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET  

@csrf_exempt
def stripe_webhook(request):
    print("\n🔹 Webhook Received!")  # ✅ Log that webhook is received

    payload = request.body
    sig_header = request.headers.get("Stripe-Signature", None)

    try:
        # ✅ Verify Stripe Signature
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        print(f"\n🔹 Full Webhook Event:\n{json.dumps(event, indent=2)}")  # ✅ Log full event
    except ValueError as e:
        print(f"\n❌ Invalid Payload: {str(e)}")
        return JsonResponse({"error": "Invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError as e:
        print(f"\n❌ Invalid Signature: {str(e)}")
        return JsonResponse({"error": "Invalid signature"}, status=400)

    # ✅ Process "checkout.session.completed" Event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        stripe_session_id = session.get("id")  # ✅ Get Stripe Session ID
        payment_intent_id = session.get("payment_intent")

        print(f"\n🔹 Processing PaymentIntent ID: {payment_intent_id}")

        # ✅ Find and Update Booking using Stripe Session ID
        booking = Booking.objects.filter(stripe_session_id=stripe_session_id).first()

        if booking:
            booking.payment_intent_id = payment_intent_id  # ✅ Save Payment Intent ID
            booking.payment_status = "paid"  # ✅ Mark as Paid
            booking.save()
            print(f"\n✅ Updated Booking {booking.id} with PaymentIntent ID: {payment_intent_id}")
        else:
            print("\n❌ No matching booking found for this payment!")

    return HttpResponse(status=200)







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
    
    
    
    
    
    
    
    
    
import base64
import hashlib
import hmac
import json

from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

def base64_url_decode(input_str):
    input_str += '=' * (-len(input_str) % 4)
    return base64.urlsafe_b64decode(input_str.encode())

@csrf_exempt
def facebook_data_deletion(request):
    if request.method == 'POST':
        signed_request = request.POST.get('signed_request')
        if not signed_request:
            return HttpResponseBadRequest("Missing signed_request")

        encoded_sig, payload = signed_request.split('.', 1)

        # Decode data
        sig = base64_url_decode(encoded_sig)
        data = json.loads(base64_url_decode(payload))

        # Verify the algorithm
        if data.get('algorithm', '').upper() != 'HMAC-SHA256':
            return HttpResponseBadRequest("Invalid algorithm")

        # Validate signature
        expected_sig = hmac.new(
            settings.FACEBOOK_APP_SECRET.encode(),
            msg=payload.encode(),
            digestmod=hashlib.sha256
        ).digest()

        if not hmac.compare_digest(sig, expected_sig):
            return HttpResponseBadRequest("Invalid signature")

        fb_user_id = data.get('user_id')

        # Delete user data from your database (example)
        from api.models import YourUserModel
        YourUserModel.objects.filter(facebook_id=fb_user_id).delete()

        response = {
            "url": "https://lockquick.com.au/deletion-confirmation/",
            "confirmation_code": fb_user_id
        }
        return JsonResponse(response)

    return HttpResponseBadRequest("Only POST allowed")