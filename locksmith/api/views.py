from rest_framework import viewsets, permissions
from .permissions import IsAdmin
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Service, AdminSettings
from .serializers import AdminSettingsSerializer
from .models import User, Locksmith, CarKeyDetails, Service, Transaction, ServiceRequest, ServiceBid,LocksmithDetails
from .serializers import UserSerializer, LocksmithSerializer, CarKeyDetailsSerializer, ServiceSerializer, TransactionSerializer, ServiceRequestSerializer, ServiceBidSerializer,LocksmithDetailsSerializer
from .serializers import UserCreateSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from django.contrib.auth import authenticate


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
            user.set_password(request.data['password'])  # Hash password
            user.save()

            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'User registered successfully',
                'user': serializer.data,
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LocksmithRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(request.data['password'])  # Hash password
            user.save()

            # Create Locksmith Profile
            locksmith = Locksmith.objects.create(user=user, is_approved=False)

            # Create LocksmithDetails instance
            locksmith_details = LocksmithDetails.objects.create(
                locksmith=locksmith,
                address=request.data['address'],
                contact_number=request.data['contact_number'],
                pcc_file=request.data['pcc_file'],
                license_file=request.data['license_file'],
                photo=request.data['photo'],
            )

            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Locksmith registered successfully, pending approval',
                'user': serializer.data,
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    
class LocksmithDetailsViewSet(viewsets.ModelViewSet):
    queryset = LocksmithDetails.objects.all()
    serializer_class = LocksmithDetailsSerializer
    permission_classes = [IsAdmin]  # Only Admin can manage locksmith details

    @action(detail=True, methods=['put'], permission_classes=[IsAdmin])
    def verify_locksmith(self, request, pk=None):
        locksmith_details = self.get_object()
        locksmith_details.is_verified = True
        locksmith_details.save()

        # Optionally, you can approve the locksmith if the details are verified
        locksmith = locksmith_details.locksmith
        locksmith.is_approved = True
        locksmith.save()

        return Response({'status': 'locksmith details verified and approved'})

    @action(detail=True, methods=['put'], permission_classes=[IsAdmin])
    def reject_locksmith(self, request, pk=None):
        locksmith_details = self.get_object()
        locksmith_details.is_verified = False
        locksmith_details.save()

        # Optionally, you can reject the locksmith if the details are rejected
        locksmith = locksmith_details.locksmith
        locksmith.is_approved = False
        locksmith.save()

        return Response({'status': 'locksmith details rejected'})

    @action(detail=True, methods=['get'], permission_classes=[IsAdmin])
    def verify_locksmith_details(self, request, pk=None):
        locksmith_details = self.get_object()

        # Collect the locksmith details to be verified
        locksmith_data = {
            "name" : locksmith_details.locksmith.user.get_full_name() or locksmith_details.locksmith.user.username(),
            "address": locksmith_details.address,
            "contact_number": locksmith_details.contact_number,
            "pcc_file": locksmith_details.pcc_file.url if locksmith_details.pcc_file else None,
            "license_file": locksmith_details.license_file.url if locksmith_details.license_file else None,
            "photo": locksmith_details.photo.url if locksmith_details.photo else None,
            "is_verified": locksmith_details.is_verified,
            "is_approved": locksmith_details.locksmith.is_approved
        }

        return Response(locksmith_data)



class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Login successful',
                'user_id': user.id,
                'username': user.username,
                'role':user.role,
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, status=status.HTTP_200_OK)
        else:
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
        return request.user.role == 'customer'  # Adjust role check for customers

# Admin Views
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]  # Only Admin can manage users

class LocksmithViewSet(viewsets.ModelViewSet):
    queryset = Locksmith.objects.all()
    serializer_class = LocksmithSerializer
    permission_classes = [IsAdmin] # Only Admin can manage locksmiths

    @action(detail=True, methods=['put'], permission_classes=[IsAdmin])
    def approve_locksmith(self, request, pk=None):
        locksmith = self.get_object()
        locksmith.is_approved = True
        locksmith.save()
        return Response({'status': 'locksmith approved'})

    @action(detail=True, methods=['put'], permission_classes=[IsAdmin])
    def reject_locksmith(self, request, pk=None):
        locksmith = self.get_object()
        locksmith.is_approved = False
        locksmith.save()
        return Response({'status': 'locksmith rejected'})
    
    
class AllLocksmiths(viewsets.ReadOnlyModelViewSet):  # Use ReadOnlyModelViewSet if only listing
    queryset = User.objects.filter(role='locksmith')
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    

class CarKeyDetailsViewSet(viewsets.ModelViewSet):
    queryset = CarKeyDetails.objects.all()
    serializer_class = CarKeyDetailsSerializer
    permission_classes = [IsAdmin]  # Only Admin can manage car key details

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAdmin]  # Only Admin can manage services

    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def platform_settings(self, request):
        # Returns platform settings like commission percentage
        platform_settings = AdminSettings.objects.first()
        return Response({'commission_percentage': platform_settings.commission_percentage, 'platform_status': platform_settings.platform_status})

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
    queryset = AdminSettings.objects.all()
    serializer_class = AdminSettingsSerializer    


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

