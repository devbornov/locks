from rest_framework import serializers
from .models import User, Locksmith, CarKeyDetails, Service, Transaction, ServiceRequest, ServiceBid, AdminSettings, PlatformStatistics

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']
        
        
        
class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, default='customer')  # Default to 'customer'

    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'password', 'first_name', 'last_name']

    def create(self, validated_data):
        """
        Create a new user with a hashed password and specified role.
        """
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user

class LocksmithSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # Read-only user data
    services_offered = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all(), many=True)

    class Meta:
        model = Locksmith
        fields = [
            'id', 'user', 'services_offered', 'service_area', 'is_approved', 
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
    commission_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    platform_status = serializers.BooleanField(default=True)

    class Meta:
        model = AdminSettings
        fields = ['commission_percentage', 'platform_status']

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
