from rest_framework import viewsets, permissions
from .permissions import IsAdmin
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Service, AdminSettings
from .serializers import AdminSettingsSerializer
from .models import User, Locksmith, CarKeyDetails, Service, Transaction, ServiceRequest, ServiceBid
from .serializers import UserSerializer, LocksmithSerializer, CarKeyDetailsSerializer, ServiceSerializer, TransactionSerializer, ServiceRequestSerializer, ServiceBidSerializer
from .serializers import UserCreateSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated


class CreateAdminUserView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]  # Only authenticated admin users can create other users

    def post(self, request):
        # Validate and create a new admin user
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save(is_staff=True)  # Set user as admin (staff)
            return Response({"message": "Admin user created successfully", "user": serializer.data})
        return Response(serializer.errors, status=400)


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
    permission_classes = [IsAdmin]  # Only Admin can manage locksmiths

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

