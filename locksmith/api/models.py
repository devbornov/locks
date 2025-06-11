from django.db import models
from django.contrib.auth.models import AbstractUser
import pyotp

# User Model with Role-Based Accessfrom django.contrib.auth.models import AbstractUser
from django.db import models
import pyotp

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('locksmith', 'Locksmith'),
        ('customer', 'Customer'),
    ]
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='customer')
    totp_secret = models.CharField(max_length=32, blank=True, null=True)  # Google Authenticator Secret
    otp_code = models.CharField(max_length=6, blank=True, null=True)  # Temporary OTP for Password Reset

    def enable_totp(self):
        """Generate a new TOTP secret key and save it in the database."""
        self.totp_secret = pyotp.random_base32()
        self.save()
        return self.totp_secret  # Return the secret for generating a QR code

    def verify_totp(self, otp_code, valid_window=1):
        """Verify the OTP entered by the user using Google Authenticator."""
        if not self.totp_secret:
            return False  # TOTP not enabled
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(otp_code, valid_window=valid_window)  # Accepts ±1 time step

    def __str__(self):
        return f"{self.username} - {self.role}"


# Admin Settings Model (For Commission & Platform Settings)  
class AdminSettings(models.Model):
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=40.00)  # Fixed commission amount
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)  # Percentage value
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)  # GST percentage
    platform_status = models.CharField(max_length=20, choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')

    def __str__(self):
        return f"Commission: {self.commission_amount} | Percentage: {self.percentage}% | GST: {self.gst_percentage}% | Status: {self.platform_status}"

    class Meta:
        verbose_name = 'Admin Settings'
        verbose_name_plural = 'Admin Settings'




class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    address = models.TextField(blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True, default="")  
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)  # ✅ Added Latitude
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)  # ✅ Added Longitude

    def __str__(self):
        return f"{self.user.username} - Customer"





# Locksmith Model
from django.core.exceptions import ValidationError

def validate_latitude(value):
    if value is not None and (value < -90 or value > 90):
        raise ValidationError("Latitude must be between -90 and 90.")

def validate_longitude(value):
    if value is not None and (value < -180 or value > 180):
        raise ValidationError("Longitude must be between -180 and 180.")

class Locksmith(models.Model):
    GST_CHOICES = [
        ('Yes', 'Yes'),
        ('No', 'No'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    service_area = models.CharField(max_length=255, default="")
    stripe_account_id = models.CharField(max_length=255, blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    reputation_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    latitude = models.DecimalField(
        max_digits=20, decimal_places=15, null=True, blank=True, validators=[validate_latitude]
    )
    longitude = models.DecimalField(
        max_digits=20, decimal_places=15, null=True, blank=True, validators=[validate_longitude]
    )
    address = models.TextField(default="")
    contact_number = models.CharField(max_length=15, blank=True, null=True, default="")
    pcc_file = models.FileField(upload_to='locksmiths/pcc/', blank=True, null=True)
    license_file = models.FileField(upload_to='locksmiths/license/', blank=True, null=True)
    photo = models.ImageField(upload_to='locksmiths/photos/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True, blank=True, null=True)

    # Updated GST field
    gst_registered = models.CharField(
        max_length=3,
        choices=GST_CHOICES,
        default='No',
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.service_area}"






# Car Key Details Model
class CarKeyDetails(models.Model):
    manufacturer = models.CharField(max_length=255)
    model = models.CharField(max_length=255)
    
    # Optional year range fields
    year_from = models.IntegerField(
        blank=True,
        null=True,
        help_text="Starting year (e.g. 2018)"
    )
    year_to = models.IntegerField(
        blank=True,
        null=True,
        help_text="Ending year (e.g. 2024)"
    )

    number_of_buttons = models.IntegerField()

    def __str__(self):
        if self.year_from and self.year_to:
            return f"{self.manufacturer} {self.model} ({self.year_from}-{self.year_to})"
        return f"{self.manufacturer} {self.model}"
    
    
    
# Locksmith Service Model
class Service(models.Model):
    locksmith = models.ForeignKey(Locksmith, on_delete=models.CASCADE)
    car_key_details = models.ForeignKey(CarKeyDetails, on_delete=models.SET_NULL, null=True, blank=True)
    service_type = models.CharField(max_length=255)  # Example: "Key Cutting", "Car Lock Repair"
    price = models.DecimalField(max_digits=10, decimal_places=2)
    details = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.service_type} - {self.locksmith.user.username}"




 
# 

 



# class AdminService(models.Model):
#     name = models.CharField(max_length=255, unique=True)
#     # base_price = models.DecimalField(max_digits=10, decimal_places=2)
#     description = models.TextField(null=True, blank=True)
    
#     def __str__(self):
#         return self.name    

class AdminService(models.Model):
    SERVICE_TYPES = [
        ('smart_lock', 'Smart Lock'),
        ('emergency', 'Emergency'),
        ('automotive', 'Automotive'),
        ('commercial', 'Commercial'),
        ('residential', 'Residential'),
    ]

    name = models.CharField(max_length=255)  # Removed unique=True
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES, null=True, blank=True)

    class Meta:
        unique_together = ('name', 'service_type')  # Enforce combo uniqueness

    def __str__(self):
        return self.name

class LocksmithServices(models.Model):
    SERVICE_TYPES = [
        ('smart_lock', 'Smart Lock'),
        ('emergency', 'Emergency'),
        ('automotive', 'Automotive'),
        ('commercial', 'Commercial'),
        ('residential', 'Residential'),
    ]

    locksmith = models.ForeignKey(Locksmith, on_delete=models.CASCADE)
    admin_service = models.ForeignKey(AdminService, on_delete=models.CASCADE)
    custom_price = models.DecimalField(max_digits=10, decimal_places=2)  # Entered by locksmith
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # Calculated
    details = models.TextField(null=True, blank=True)
    approved = models.BooleanField(default=False)
    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_TYPES,
        default='residential'
    )
    additional_key_price = models.DecimalField(
    max_digits=10, decimal_places=2, default=0.00,
    help_text="Price charged per additional key"
    )
    # ✅ ADD THIS ForeignKey for car key details
    car_key_details = models.ForeignKey(
        CarKeyDetails, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"{self.admin_service.name} - {self.locksmith.user.username} ({self.service_type})"

    

# Bidding Model (Customers Place Bids for Service)
class ServiceBid(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    locksmith = models.ForeignKey(Locksmith, on_delete=models.CASCADE)
    service = models.ForeignKey(LocksmithServices, on_delete=models.CASCADE)
    bid_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bid {self.id} - {self.status} ({self.customer.username})"
    
    
    

# Service Request Model
class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_requests')
    locksmith = models.ForeignKey(Locksmith, on_delete=models.CASCADE, related_name='locksmith_requests')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    service_area = models.CharField(max_length=255, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def accept(self):
        """Locksmith accepts the service request"""
        self.status = 'accepted'
        self.save()

    def reject(self):
        """Locksmith rejects the service request"""
        self.status = 'rejected'
        self.save()

    def complete(self):
        """Service is marked as completed"""
        self.status = 'completed'
        self.save()

    def __str__(self):
        return f"Request by {self.customer.username} for {self.service.service_type} - {self.status}"
    
    
    
# Service Request Model (For Customers Requesting Locksmith Services)
class CustomerServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    locksmith = models.ForeignKey(Locksmith, on_delete=models.CASCADE)
    service = models.ForeignKey(LocksmithServices, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request by {self.customer.user.username} for {self.service.service_type} - Status: {self.status}"    
    
    


# Transaction Model (For Payment & Commission)
class Transaction(models.Model):
    customer = models.ForeignKey(User, related_name='customer_transactions', on_delete=models.SET_NULL, null=True)
    locksmith = models.ForeignKey(Locksmith, related_name='locksmith_transactions', on_delete=models.SET_NULL, null=True)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission = models.DecimalField(max_digits=10, decimal_places=2)  # Admin takes commission
    status = models.CharField(max_length=50, choices=[('pending', 'Pending'), ('paid', 'Paid')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    payment_intent_id = models.CharField(max_length=255, blank=True, null=True)  # ✅ Store Stripe PaymentIntent ID

    def mark_as_paid(self):
        """Mark transaction as paid"""
        self.status = 'paid'
        self.save()

    def __str__(self):
        return f"Transaction {self.id} - {self.status}"

# Statistics Model (For Admin Dashboard)
class PlatformStatistics(models.Model):
    total_transactions = models.IntegerField(default=0)
    total_locksmiths = models.IntegerField(default=0)
    total_customers = models.IntegerField(default=0)
    most_popular_service = models.CharField(max_length=255, null=True, blank=True)
    top_locksmith = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Platform Stats - {self.total_transactions} Transactions"




# class Booking(models.Model):
#     customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
#     locksmith_service = models.ForeignKey(LocksmithServices, on_delete=models.CASCADE)
#     scheduled_date = models.DateTimeField()
#     status = models.CharField(
#         max_length=20, choices=[('Scheduled', 'Scheduled'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')], default='Scheduled'
#     )
#     payment_intent_id = models.CharField(max_length=255, blank=True, null=True)  # ✅ Store Stripe PaymentIntent ID
#     stripe_session_id = models.CharField(max_length=255, blank=True, null=True)  # ✅ Store Stripe Session ID
#     payment_status = models.CharField(max_length=20, choices=[
#         ("pending", "Pending"),
#         ("paid", "Paid"),
#         ("refunded", "Refunded"),
#         ("canceled", "Canceled")   
#     ], default="pending")  # ✅ Store Payment Status

#     def complete(self):
#         self.status = 'Completed'
#         self.save()

#     def cancel(self):
#         self.status = 'Cancelled'
#         self.save()
class Booking(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    locksmith_service = models.ForeignKey(LocksmithServices, on_delete=models.CASCADE)
    scheduled_date = models.DateTimeField()
    locksmith_status = models.CharField(
        max_length=10,
        choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('DENIED', 'Denied')],
        default='PENDING'
    )
    # New customer fields
    customer_contact_number = models.CharField(max_length=20, blank=True, null=True)
    customer_address = models.TextField(blank=True, null=True)
    house_number = models.CharField(max_length=20, blank=True, null=True)
    number_of_keys = models.PositiveIntegerField(
        blank=True, null=True, help_text="Optional: number of keys the customer wants"
    )
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        help_text="Total price including base service and keys"
    )
    
    emergency = models.BooleanField(default=False, help_text="Is this an emergency service?")

    # Booking status
    status = models.CharField(
        max_length=20,
        choices=[('Scheduled', 'Scheduled'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')],
        default='Scheduled'
    )
    payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("refunded", "Refunded"),
            ("canceled", "Canceled")
        ],
        default="pending"
    )
    image = models.ImageField(upload_to='booking_images/', blank=True, null=True, help_text="Optional image related to the booking")
    
    is_customer_confirmed = models.BooleanField(default=False)
    is_locksmith_confirmed = models.BooleanField(default=False)

    def check_completion(self):
        if self.is_customer_confirmed and self.is_locksmith_confirmed:
            self.status = 'Completed'
            self.payment_status = 'paid'
            self.save()

    def complete(self):
        self.status = 'Completed'
        self.save()

    def cancel(self):
        self.status = 'Cancelled'
        self.save()

        
        
        
        
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.subject
    
    
    
    
