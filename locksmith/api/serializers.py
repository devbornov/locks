import pyotp
import qrcode
import base64
import os
from io import BytesIO
from decimal import Decimal
from django.conf import settings
from rest_framework import serializers
from .models import User, Locksmith, Customer, CustomerServiceRequest , CarKeyDetails, Service, Transaction, ServiceRequest, ServiceBid, AdminSettings, PlatformStatistics,LocksmithServices,AdminService , Booking , ContactMessage
from dj_rest_auth.registration.serializers import SocialLoginSerializer
from allauth.socialaccount.models import SocialAccount

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']
        
        
        
# class UserCreateSerializer(serializers.ModelSerializer):
#     totp_enabled = serializers.BooleanField(default=False, required=False)

#     class Meta:
#         model = User
#         fields = ['id', 'username', 'email', 'password', 'role', 'totp_enabled']
#         extra_kwargs = {'password': {'write_only': True}}

#     def create(self, validated_data):
#         totp_enabled = validated_data.pop('totp_enabled', False)
#         password = validated_data.pop('password')

#         user = User.objects.create(**validated_data)
#         user.set_password(password)

#         if totp_enabled:
#             user.totp_secret = pyotp.random_base32()
#         else:
#             user.totp_secret = None
        
#         user.totp_enabled = totp_enabled
#         user.save()

#         return user

#     def get_totp_details(self, user):
#         """Generate and return the TOTP secret and QR code."""
#         if not user.totp_secret:
#             return {"totp_secret": None, "totp_qr_code": None, "qr_code_url": None}

#         # Generate TOTP URI
#         totp_uri = pyotp.totp.TOTP(user.totp_secret).provisioning_uri(
#             name=user.email, issuer_name="locksmith"
#         )

#         # Generate QR Code
#         qr = qrcode.make(totp_uri)
        
#         # Define QR Code Save Path
#         qr_folder = os.path.join(settings.MEDIA_ROOT, "Customer_qr_codes")
#         os.makedirs(qr_folder, exist_ok=True)  # Ensure directory exists

#         qr_filename = f"{user.username}.png"
#         qr_path = os.path.join(qr_folder, qr_filename)
#         qr.save(qr_path)  # Save QR Code

#         # Convert QR Code to Base64
#         buffered = BytesIO()
#         qr.save(buffered, format="PNG")
#         qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

#         # Generate Public URL for QR Code (if MEDIA_URL is set)
#         qr_code_url = f"{settings.MEDIA_URL}Customer_qr_codes/{qr_filename}"

#         return {
#             "totp_secret": user.totp_secret,  # Include raw TOTP key
#             "totp_qr_code": f"data:image/png;base64,{qr_base64}",  # Base64 QR Code
#             "qr_code_url": qr_code_url  # URL to access the saved QR code
#         }




# class UserCreateSerializer(serializers.ModelSerializer):
#     totp_enabled = serializers.BooleanField(default=False, required=False)

#     class Meta:
#         model = User
#         fields = ['id', 'username', 'email', 'password', 'role', 'totp_enabled']
#         extra_kwargs = {'password': {'write_only': True}}

#     def create(self, validated_data):
#         totp_enabled = validated_data.pop('totp_enabled', False)
#         password = validated_data.pop('password')

#         user = User(**validated_data)
#         user.set_password(password)

#         if totp_enabled:
#             user.totp_secret = pyotp.random_base32()
#         else:
#             user.totp_secret = None

#         user.save()
#         return user

#     def get_totp_details(self, user):
#         if not user.totp_secret:
#             return {"totp_secret": None, "totp_qr_code": None, "qr_code_url": None}

#         # ✅ Generate URI for Google Authenticator
#         totp_uri = pyotp.TOTP(user.totp_secret).provisioning_uri(
#             name=user.email,
#             issuer_name="LockQuick"
#         )

#         # ✅ Create QR code
#         qr = qrcode.make(totp_uri)

#         # ✅ Define QR code folder by role
#         folder_name = "Customer_qr_codes" if user.role == "customer" else "Locksmith_qr_codes"
#         qr_folder = os.path.join(settings.MEDIA_ROOT, folder_name)
#         os.makedirs(qr_folder, exist_ok=True)

#         qr_filename = f"{user.username}.png"
#         qr_path = os.path.join(qr_folder, qr_filename)
#         qr.save(qr_path)

#         # ✅ Convert QR to base64
#         buffered = BytesIO()
#         qr.save(buffered, format="PNG")
#         qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

#         qr_code_url = f"{settings.MEDIA_URL}{folder_name}/{qr_filename}"

#         return {
#             "totp_secret": user.totp_secret,
#             "totp_qr_code": f"data:image/png;base64,{qr_base64}",
#             "qr_code_url": qr_code_url
#         }

class UserCreateSerializer(serializers.ModelSerializer):
    totp_enabled = serializers.BooleanField(default=False, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role', 'totp_enabled']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        totp_enabled = validated_data.pop('totp_enabled', False)
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.set_password(password)

        if totp_enabled:
            user.totp_secret = pyotp.random_base32()
        else:
            user.totp_secret = None

        user.save()
        return user

    def get_totp_details(self, user):
        if not user.totp_secret:
            return {
                "totp_secret": None,
                "totp_qr_code": None,
                "qr_code_url": None
            }

        # ✅ Generate provisioning URI for Google Authenticator
        totp_uri = pyotp.TOTP(user.totp_secret).provisioning_uri(
            name=user.email,
            issuer_name="LockQuick"
        )

        # ✅ Generate QR Code
        qr = qrcode.make(totp_uri)

        # ✅ Define save location by role
        folder_name = "Customer_qr_codes" if user.role == "customer" else "Locksmith_qr_codes"
        qr_folder = os.path.join(settings.MEDIA_ROOT, folder_name)
        os.makedirs(qr_folder, exist_ok=True)

        # ✅ Save QR code image
        qr_filename = f"{user.username}.png"
        qr_path = os.path.join(qr_folder, qr_filename)
        qr.save(qr_path)

        # ✅ Convert to Base64 string
        buffered = BytesIO()
        qr.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # ✅ Public media URL for access
        qr_code_url = f"{settings.MEDIA_URL}{folder_name}/{qr_filename}"

        return {
            "totp_secret": user.totp_secret,
            "totp_qr_code": f"data:image/png;base64,{qr_base64}",
            "qr_code_url": qr_code_url
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
    username = serializers.CharField(source='user.username', required=True)  # Allow updating username

    class Meta:
        model = Customer
        fields = ['id', 'username', 'address', 'contact_number', 'latitude', 'longitude']  # ✅ Include username

    def update(self, instance, validated_data):
        # Update the username if provided
        user_data = validated_data.pop('user', {})
        if 'username' in user_data:
            instance.user.username = user_data['username']
            instance.user.save()

        return super().update(instance, validated_data)# ✅ Added Lat & Long


class LocksmithSerializer(serializers.ModelSerializer):
    user = LocksmithCreateSerializer(read_only=True)
    stripe_account_id = serializers.CharField(read_only=True)
    gst_registered = serializers.ChoiceField(choices=[('Yes', 'Yes'), ('No', 'No')], required=False)

    class Meta:
        model = Locksmith
        fields = [
            'id', 'user', 'service_area', 'is_approved',
            'address', 'contact_number', 'latitude', 'longitude',
            'pcc_file', 'license_file', 'photo', 'is_verified',
            'stripe_account_id', 'is_available',
            'gst_registered'  # ✅ Include this field
        ]

    def validate_service_area(self, value):
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
        
        
        
        
# class LocksmithServiceSerializer(serializers.ModelSerializer):
#     car_key_details = CarKeyDetailsSerializer(read_only=True)
#     locksmith = LocksmithSerializer(read_only=True)
#     price = serializers.DecimalField(max_digits=10, decimal_places=2)

#     class Meta:
#         model = LocksmithServices
#         fields = ['id', 'locksmith', 'service_type', 'car_key_details', 'price', 'details']





class TransactionSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)
    locksmith = LocksmithSerializer(read_only=True)
    customer = UserSerializer(read_only=True)
    commission = serializers.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = serializers.DateTimeField()
    payment_intent_id = serializers.CharField(read_only=True)  # ✅ Add Stripe PaymentIntent ID

    class Meta:
        model = Transaction
        fields = ['id', 'service', 'locksmith', 'customer', 'amount', 'commission', 
                  'transaction_date', 'status', 'payment_intent_id']  # ✅ Include Stripe PaymentIntent


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
    class Meta:
        model = AdminSettings
        fields = ['commission_amount', 'percentage', 'gst_percentage', 'platform_status']

    def update(self, instance, validated_data):
        instance.commission_amount = validated_data.get('commission_amount', instance.commission_amount)
        instance.percentage = validated_data.get('percentage', instance.percentage)
        instance.gst_percentage = validated_data.get('gst_percentage', instance.gst_percentage)
        instance.platform_status = validated_data.get('platform_status', instance.platform_status)
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





# class LocksmithServiceSerializer(serializers.ModelSerializer):
#     admin_service_id = serializers.PrimaryKeyRelatedField(
#         queryset=AdminService.objects.all(),
#         source='admin_service'
#     )
#     admin_service_name = serializers.SerializerMethodField()
#     locksmith_name = serializers.SerializerMethodField()
#     is_available = serializers.SerializerMethodField()

#     class Meta:
#         model = LocksmithServices
#         fields = [
#             'id', 'locksmith_name', 'is_available', 'admin_service_id',
#             'admin_service_name', 'service_type', 'custom_price',
#             'total_price', 'details', 'approved'
#         ]
#         read_only_fields = ['total_price']

#     def get_admin_service_name(self, obj):
#         return obj.admin_service.name if obj.admin_service else None

#     def get_locksmith_name(self, obj):
#         return obj.locksmith.user.username if obj.locksmith else None
    
#     def get_is_available(self, obj):
#         return obj.locksmith.is_available


class LocksmithServiceSerializer(serializers.ModelSerializer):
    admin_service_id = serializers.PrimaryKeyRelatedField(
        queryset=AdminService.objects.all(),
        source='admin_service'
    )
    additional_key_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    admin_service_name = serializers.SerializerMethodField()
    locksmith_name = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    car_key_details = CarKeyDetailsSerializer(required=False)  # Include CarKeyDetails
    

    class Meta:
        model = LocksmithServices
        fields = [
            'id', 'locksmith_name', 'is_available', 'admin_service_id',
            'admin_service_name', 'service_type', 'custom_price',
            'additional_key_price',  # ✅ new field
            'total_price', 'details', 'approved', 'car_key_details'
        ]
        read_only_fields = ['total_price']

    def get_admin_service_name(self, obj):
        return obj.admin_service.name if obj.admin_service else None

    def get_locksmith_name(self, obj):
        return obj.locksmith.user.username if obj.locksmith else None
    
    def get_is_available(self, obj):
        return obj.locksmith.is_available

    def validate(self, data):
        """Ensure car_key_details is provided for automotive services."""
        if data.get('service_type') == 'automotive' and not data.get('car_key_details'):
            raise serializers.ValidationError({
                "car_key_details": "Car key details are required for automotive services."
            })
        return data

    def create(self, validated_data):
        """Handles Locksmith Service creation with Car Key Details if applicable."""

        # Extract car_key_details separately
        car_key_details_data = validated_data.pop("car_key_details", None)
        car_key_details = None  

        if car_key_details_data:
            if isinstance(car_key_details_data, dict):
                # ✅ Ensure the new CarKeyDetails is saved and assigned
                car_key_details = CarKeyDetails.objects.create(**car_key_details_data)
            elif isinstance(car_key_details_data, CarKeyDetails):
                car_key_details = car_key_details_data

        # ✅ Set auto-approval for now
        validated_data['approved'] = True

        # ✅ Create Locksmith Service instance with the assigned car_key_details
        locksmith_service = LocksmithServices.objects.create(
            **validated_data, 
            car_key_details=car_key_details
        )

        return locksmith_service



# class AdminServiceSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = AdminService
#         fields = ['id', 'name', 'description']
        
class AdminServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminService
        fields = ['id', 'name', 'service_type']
        
    def validate(self, attrs):
        name = attrs.get('name')
        service_type = attrs.get('service_type')

        if AdminService.objects.filter(name__iexact=name, service_type=service_type).exists():
            raise serializers.ValidationError(
                f"A service with name '{name}' already exists under service type '{service_type}'."
            )
        return attrs

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





# class BookingSerializer(serializers.ModelSerializer):
#     customer = UserSerializer(read_only=True)  # Fetches customer details
#     locksmith_service_type = serializers.SerializerMethodField()
#     payment_intent_id = serializers.CharField(read_only=True)  # ✅ Add Stripe PaymentIntent ID

#     class Meta:
#         model = Booking
#         fields = '__all__'
#         read_only_fields = ['customer', 'status', 'locksmith_service_type', 'payment_intent_id']  # ✅ Prevent modification

#     def get_locksmith_service_type(self, obj):
#         return obj.locksmith_service.service_type if obj.locksmith_service else None


# class BookingSerializer(serializers.ModelSerializer):
#     customer = UserSerializer(read_only=True)
#     locksmith_service_type = serializers.SerializerMethodField()
#     payment_intent_id = serializers.CharField(read_only=True)

#     # New fields
#     customer_contact_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
#     customer_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
#     number_of_keys = serializers.IntegerField(required=False, allow_null=True)
#     emergency = serializers.BooleanField(required=False)

#     class Meta:
#         model = Booking
#         fields = '__all__'
#         read_only_fields = ['customer', 'status', 'locksmith_service_type', 'payment_intent_id']

#     def get_locksmith_service_type(self, obj):
#         return obj.locksmith_service.service_type if obj.locksmith_service else None



class BookingSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    locksmith_service_type = serializers.SerializerMethodField()
    payment_intent_id = serializers.CharField(read_only=True)

    # New fields (already present in your model)
    customer_contact_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    customer_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    number_of_keys = serializers.IntegerField(required=False, allow_null=True)
    emergency = serializers.BooleanField(required=False)

    # Include new model fields
    charge_id = serializers.CharField(read_only=True)
    transfer_status = serializers.CharField(read_only=True)
    locksmith_transfer_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = [
            'customer',
            'status',
            'locksmith_service_type',
            'payment_intent_id',
            'charge_id',
            'transfer_status',
            'locksmith_transfer_amount'
        ]

    def get_locksmith_service_type(self, obj):
        return obj.locksmith_service.service_type if obj.locksmith_service else None






class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = '__all__'
        
        
        
        
        
        
class CustomSocialLoginSerializer(SocialLoginSerializer):
    def validate(self, attrs):
        attrs['callback_url'] = settings.SOCIAL_AUTH_GOOGLE_CALLBACK_URL
        return super().validate(attrs)

    def save(self, request):
        user = super().save(request)

        if user.role == 'admin':
            raise serializers.ValidationError("Admins cannot sign up via social login.")

        # Update email from Google data
        social_account = SocialAccount.objects.get(user=user)
        user.email = social_account.extra_data.get('email', user.email)
        user.save()

        # Create profile based on role
        if user.role == 'customer' and not hasattr(user, 'customer'):
            Customer.objects.create(user=user)

        if user.role == 'locksmith' and not hasattr(user, 'locksmith'):
            Locksmith.objects.create(user=user)

        return user
    




# phase 2
    
    
# serializers.py
from rest_framework import serializers
from .models import WebsiteContent , SuggestedService , CCTVTechnicianPreRegistration

class WebsiteContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteContent
        fields = '__all__'

    
    
    
class SuggestedServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuggestedService
        fields = '__all__'
        read_only_fields = ['status', 'suggested_by', 'created_at']

    def validate(self, attrs):
        if attrs.get('service_type') == 'automotive':
            if not attrs.get('car_key_details'):
                raise serializers.ValidationError("Car key details are required for automotive services.")
            if not isinstance(attrs['car_key_details'], list):
                raise serializers.ValidationError("Car key details must be a list.")
            for entry in attrs['car_key_details']:
                required_fields = ['manufacturer', 'model', 'year_from', 'year_to', 'number_of_buttons']
                for field in required_fields:
                    if field not in entry:
                        raise serializers.ValidationError(f"Missing '{field}' in car key details.")
        return attrs
    
    
    
    
    
    
    
    
class CCTVTechnicianPreRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CCTVTechnicianPreRegistration
        fields = '__all__'