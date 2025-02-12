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
    commission_amount = models.DecimalField(max_digits=5, decimal_places=2, default=14.00)  # Example: 10%
    platform_status = models.CharField(max_length=20, choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')

    def __str__(self):
        return f"Platform Settings - Commission: {self.commission_percentage}% | Status: {self.platform_status}"

    class Meta:
        verbose_name = 'Admin Settings'
        verbose_name_plural = 'Admin Settings'



class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    address = models.TextField(blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True, default="")  # Optional

    def __str__(self):
        return f"{self.user.username} - Customer"




# Locksmith Model
class Locksmith(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    service_area = models.CharField(max_length=255, default="")  # Ensure default for service area
    is_approved = models.BooleanField(default=False)  # Admin approves locksmiths
    reputation_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)  # Reputation Score
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    address = models.TextField(default="")  # Default empty string to prevent null issues
    contact_number = models.CharField(max_length=15, blank=True, null=True, default="")  # Allow blank/null
    pcc_file = models.FileField(upload_to='locksmiths/pcc/', blank=True, null=True)  # Allow file to be optional
    license_file = models.FileField(upload_to='locksmiths/license/', blank=True, null=True)  # Allow blank/null
    photo = models.ImageField(upload_to='locksmiths/photos/', blank=True, null=True)  # Allow blank/null
    is_verified = models.BooleanField(default=False)  # Initially not verified

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
    
    
    
class LocksmithService(models.Model):
    SERVICE_TYPES = [
        ('key_duplication', 'Key Duplication'),
        ('car_key_repair', 'Car Key Repair'),
        ('home_lock_repair', 'Home Lock Repair'),
        ('locked_unlocking', 'Locked Unlocking'),
    ]

    locksmith = models.ForeignKey(Locksmith, on_delete=models.CASCADE)
    car_key_details = models.ForeignKey(CarKeyDetails, on_delete=models.SET_NULL, null=True, blank=True)
    service_type = models.CharField(max_length=255, choices=SERVICE_TYPES, default='key_duplication')  
    price = models.DecimalField(max_digits=10, decimal_places=2)
    details = models.TextField(null=True, blank=True)

    def total_cost(self):
        """Calculate total cost including fixed admin commission amount"""
        admin_settings = AdminSettings.objects.first()  # Get the admin settings
        if admin_settings:
            return self.price + admin_settings.commission_amount  # Add fixed amount
        return self.price  # Default if no admin settings exist

    def __str__(self):
        return f"{self.service_type} - {self.locksmith.user.username} (Total Cost: {self.total_cost()})"
    
    def __str__(self):
        return f"{self.service_type} - {self.locksmith.user.username}"
    
    
    
    

# Bidding Model (Customers Place Bids for Service)
class ServiceBid(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    locksmith = models.ForeignKey(Locksmith, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
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
    service = models.ForeignKey(LocksmithService, on_delete=models.CASCADE)
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
