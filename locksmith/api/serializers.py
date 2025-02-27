import pyotp
import qrcode
import base64
import os
from io import BytesIO
from django.conf import settings
from rest_framework import serializers
from .models import User, Locksmith, Customer, CustomerServiceRequest , CarKeyDetails, Service, Transaction, ServiceRequest, ServiceBid, AdminSettings, PlatformStatistics,LocksmithServices,AdminService

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']
        
        
        
class UserCreateSerializer(serializers.ModelSerializer):
    totp_enabled = serializers.BooleanField(default=False, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role', 'totp_enabled']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        totp_enabled = validated_data.pop('totp_enabled', False)
        password = validated_data.pop('password')

        user = User.objects.create(**validated_data)
        user.set_password(password)

        if totp_enabled:
            user.totp_secret = pyotp.random_base32()
        else:
            user.totp_secret = None
        
        user.totp_enabled = totp_enabled
        user.save()

        return user

    def get_totp_details(self, user):
        """Generate and return the TOTP secret and QR code."""
        if not user.totp_secret:
            return {"totp_secret": None, "totp_qr_code": None, "qr_code_url": None}

        # Generate TOTP URI
        totp_uri = pyotp.totp.TOTP(user.totp_secret).provisioning_uri(
            name=user.email, issuer_name="locksmith"
        )

        # Generate QR Code
        qr = qrcode.make(totp_uri)
        
        # Define QR Code Save Path
        qr_folder = os.path.join(settings.MEDIA_ROOT, "Customer_qr_codes")
        os.makedirs(qr_folder, exist_ok=True)  # Ensure directory exists

        qr_filename = f"{user.username}.png"
        qr_path = os.path.join(qr_folder, qr_filename)
        qr.save(qr_path)  # Save QR Code

        # Convert QR Code to Base64
        buffered = BytesIO()
        qr.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Generate Public URL for QR Code (if MEDIA_URL is set)
        qr_code_url = f"{settings.MEDIA_URL}Customer_qr_codes/{qr_filename}"

        return {
            "totp_secret": user.totp_secret,  # Include raw TOTP key
            "totp_qr_code": f"data:image/png;base64,{qr_base64}",  # Base64 QR Code
            "qr_code_url": qr_code_url  # URL to access the saved QR code
        }


class LocksmithCreateSerializer(serializers.ModelSerializer):
    totp_enabled = serializers.BooleanField(default=False, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role', 'totp_enabled']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        totp_enabled = validated_data.pop('totp_enabled', False)
        password = validated_data.pop('password')

        user = User.objects.create(**validated_data)
        user.set_password(password)

        if totp_enabled:
            user.totp_secret = pyotp.random_base32()
        else:
            user.totp_secret = None

        user.totp_enabled = totp_enabled
        user.role = "locksmith"  # Ensure role is always 'locksmith'
        user.save()

        return user

    def get_totp_details(self, user):
        """Generate and return the TOTP secret and QR code for locksmiths."""
        if not user.totp_secret:
            return {"totp_secret": None, "totp_qr_code": None, "qr_code_url": None}

        # Generate TOTP URI
        totp_uri = pyotp.totp.TOTP(user.totp_secret).provisioning_uri(
            name=user.email, issuer_name="locksmith"
        )

        # Generate QR Code
        qr = qrcode.make(totp_uri)

        # Define QR Code Save Path for Locksmiths
        qr_folder = os.path.join(settings.MEDIA_ROOT, "Locksmith_qr_codes")
        os.makedirs(qr_folder, exist_ok=True)  # Ensure directory exists

        qr_filename = f"{user.username}.png"
        qr_path = os.path.join(qr_folder, qr_filename)
        qr.save(qr_path)  # Save QR Code

        # Convert QR Code to Base64
        buffered = BytesIO()
        qr.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Generate Public URL for QR Code (if MEDIA_URL is set)
        qr_code_url = f"{settings.MEDIA_URL}Locksmith_qr_codes/{qr_filename}"

        return {
            "totp_secret": user.totp_secret,  # Include raw TOTP key
            "totp_qr_code": f"data:image/png;base64,{qr_base64}",  # Base64 QR Code
            "qr_code_url": qr_code_url  # URL to access the saved QR code
        }





# Customer Serializer
class CustomerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Customer
        fields = ['id', 'user', 'address', 'contact_number']

class LocksmithSerializer(serializers.ModelSerializer):
    user = LocksmithCreateSerializer(read_only=True)  # Read-only user data
    # services_offered = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all(), many=True)

    class Meta:
        model = Locksmith
        fields = [
            'id', 'user', 'service_area', 'is_approved',
            'address', 'contact_number', 'pcc_file', 'license_file', 'photo', 'is_verified'
        ]

    def validate_service_area(self, value):
        # Validate the service area format if necessary
        return value


class CarKeyDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarKeyDetails
        fields = '__all__'

class ServiceSerializer(serializers.ModelSerializer):
    car_key_details = CarKeyDetailsSerializer(read_only=True)
    locksmith = LocksmithSerializer(read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = Service
        fields = ['id', 'locksmith', 'service_type', 'car_key_details', 'price', 'details']
        
        
        
        
class LocksmithServiceSerializer(serializers.ModelSerializer):
    car_key_details = CarKeyDetailsSerializer(read_only=True)
    locksmith = LocksmithSerializer(read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = LocksmithServices
        fields = ['id', 'locksmith', 'service_type', 'car_key_details', 'price', 'details']





class TransactionSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)
    locksmith = LocksmithSerializer(read_only=True)
    customer = UserSerializer(read_only=True)
    commission = serializers.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = serializers.DateTimeField()

    class Meta:
        model = Transaction
        fields = ['id', 'service', 'locksmith', 'customer', 'amount', 'commission', 'transaction_date', 'status']

class ServiceRequestSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    locksmith = LocksmithSerializer(read_only=True)
    service_details = ServiceSerializer(read_only=True)
    status = serializers.ChoiceField(choices=["PENDING", "ACCEPTED", "COMPLETED", "REJECTED"], default="PENDING")
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)

    class Meta:
        model = ServiceRequest
        fields = ['id', 'customer', 'locksmith', 'service_details', 'status', 'request_date', 'latitude', 'longitude']

    def validate_service_details(self, value):
        # Ensure the service request is valid
        return value

class ServiceBidSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    locksmith = LocksmithSerializer(read_only=True)
    service_request = ServiceRequestSerializer(read_only=True)
    bid_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    bid_status = serializers.ChoiceField(choices=["pending", "accepted", "rejected"], default="pending")
    bid_date = serializers.DateTimeField()

    class Meta:
        model = ServiceBid
        fields = ['id', 'customer', 'locksmith', 'service_request', 'bid_amount', 'bid_status', 'bid_date']

    def validate_bid_amount(self, value):
        # Ensure the bid amount is appropriate
        return value

class AdminSettingsSerializer(serializers.ModelSerializer):
    commission_amount = serializers.DecimalField(max_digits=5, decimal_places=2)
    platform_status = serializers.BooleanField(default=True)

    class Meta:
        model = AdminSettings
        fields = ['commission_amount', 'platform_status']

    def update_commission(self, instance, validated_data):
        # Logic to update platform settings such as commission percentage
        instance.commission_percentage = validated_data.get('commission_percentage', instance.commission_percentage)
        instance.save()
        return instance

class PlatformStatisticsSerializer(serializers.ModelSerializer):
    total_transactions = serializers.IntegerField()
    total_locksmiths = serializers.IntegerField()
    total_customers = serializers.IntegerField()
    most_popular_service = serializers.CharField(max_length=255, required=False, allow_blank=True)
    top_locksmith = serializers.CharField(max_length=255, required=False, allow_blank=True)

    class Meta:
        model = PlatformStatistics
        fields = ['total_transactions', 'total_locksmiths', 'total_customers', 'most_popular_service', 'top_locksmith']





class LocksmithServiceSerializer(serializers.ModelSerializer):
    admin_service_id = serializers.PrimaryKeyRelatedField(
        queryset=AdminService.objects.all(),
        source='admin_service'
    )
    admin_service_name = serializers.SerializerMethodField()
    locksmith_name = serializers.SerializerMethodField()  # New field for locksmith's name

    class Meta:
        model = LocksmithServices
        fields = ['id', 'locksmith_name', 'admin_service_id', 'admin_service_name', 'service_type', 'custom_price', 'total_price', 'details', 'approved']
        read_only_fields = ['total_price']

    def get_admin_service_name(self, obj):
        return obj.admin_service.name if obj.admin_service else None

    def get_locksmith_name(self, obj):
        """Retrieve the associated locksmith's username."""
        return obj.locksmith.user.username if obj.locksmith else None

    def create(self, validated_data):
        """Assign locksmith based on logged-in user."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError({"error": "User must be authenticated."})

        try:
            locksmith = request.user.locksmith  # Get locksmith instance from authenticated user
        except AttributeError:
            raise serializers.ValidationError({"error": "User is not associated with a locksmith account."})

        validated_data['locksmith'] = locksmith  # Assign locksmith automatically
        return super().create(validated_data)

    def get_total_cost(self, obj):
        return obj.total_cost()


class AdminServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminService
        fields = ['id', 'name', 'base_price', 'description']
        
        

# class LocksmithServiceSerializer(serializers.ModelSerializer):
#     total_cost = serializers.SerializerMethodField()
#     car_key_details = CarKeyDetailsSerializer(read_only=True)
#     locksmith = LocksmithSerializer(read_only=True)
#     price = serializers.DecimalField(max_digits=10, decimal_places=2)

#     class Meta:
#         model = LocksmithService
#         fields = ['id', 'locksmith', 'car_key_details','service_type', 'price', 'details', 'total_cost']

#     def get_total_cost(self, obj):
#         return obj.total_cost()  # Call total cost method



# Service Request Serializer
class CustomerServiceRequestSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    locksmith = LocksmithSerializer(read_only=True)
    service = LocksmithServiceSerializer(read_only=True)

    class Meta:
        model = CustomerServiceRequest
        fields = ['id', 'customer', 'locksmith', 'service', 'status', 'requested_at']


        