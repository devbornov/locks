from django.db import models
from django.contrib.auth.models import AbstractUser
import pyotp

# User Model with Role-Based Access
class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('locksmith', 'Locksmith'),
        ('customer', 'Customer'),
    ]
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='customer')
    totp_secret = models.CharField(max_length=32, blank=True, null=True)  # Optional TOTP Secret

    def enable_totp(self):
        """Generate a TOTP secret key for the user if they enable TOTP."""
        if not self.totp_secret:
            self.totp_secret = pyotp.random_base32()
            self.save()

    def verify_totp(self, otp_code, valid_window=1):
        """Verify the OTP code entered by the user."""
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
    platform_status = models.CharField(max_length=20, choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')

    def __str__(self):
        return f"Commission: {self.commission_amount} | Percentage: {self.percentage}% | Status: {self.platform_status}"

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
class Locksmith(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    service_area = models.CharField(max_length=255, default="")
    stripe_account_id = models.CharField(max_length=255, blank=True, null=True)  # ✅ Store Stripe ID
    is_approved = models.BooleanField(default=False)
    reputation_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    address = models.TextField(default="")
    contact_number = models.CharField(max_length=15, blank=True, null=True, default="")
    pcc_file = models.FileField(upload_to='locksmiths/pcc/', blank=True, null=True)
    license_file = models.FileField(upload_to='locksmiths/license/', blank=True, null=True)
    photo = models.ImageField(upload_to='locksmiths/photos/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True , blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.service_area}"




# Car Key Details Model
class CarKeyDetails(models.Model):
    manufacturer = models.CharField(max_length=255)
    model = models.CharField(max_length=255)
    year = models.IntegerField()
    number_of_buttons = models.IntegerField()

    def __str__(self):
        return f"{self.manufacturer} {self.model} ({self.year})"

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

 



class AdminService(models.Model):
    name = models.CharField(max_length=255, unique=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(null=True, blank=True)
    
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




class Booking(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    locksmith_service = models.ForeignKey(LocksmithServices, on_delete=models.CASCADE)
    scheduled_date = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=[('Scheduled', 'Scheduled'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')], default='Scheduled'
    )
    payment_intent_id = models.CharField(max_length=255, blank=True, null=True)  # ✅ Store Stripe PaymentIntent ID
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)  # ✅ Store Stripe Session ID
    payment_status = models.CharField(max_length=20, choices=[
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("refunded", "Refunded"),
        ("canceled", "Canceled")
    ], default="pending")  # ✅ Store Payment Status

    def complete(self):
        self.status = 'Completed'
        self.save()

    def cancel(self):
        self.status = 'Cancelled'
        self.save()