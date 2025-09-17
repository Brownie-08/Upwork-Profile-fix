from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from profiles.models import Vehicle

class TransportRequest(models.Model):
    SERVICE_TYPE_CHOICES = [
        ('TAXI', 'Taxi'),
        ('DELIVERY', 'Delivery'),
    ]

    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('ACCEPTED', 'Accepted'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_requests')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='provided_jobs', null=True, blank=True)
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES, default='TAXI')
    
    pickup_location = models.CharField(max_length=255)
    pickup_latitude = models.FloatField()
    pickup_longitude = models.FloatField()
    dropoff_location = models.CharField(max_length=255)
    dropoff_latitude = models.FloatField()
    dropoff_longitude = models.FloatField()

    pickup_time = models.DateTimeField()
    budget = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    distance_km = models.FloatField(validators=[MinValueValidator(0)])
    route_polyline = models.TextField(null=True, blank=True, help_text="Encoded polyline for the route")
    estimated_time = models.IntegerField(help_text="Estimated travel time in minutes", null=True, blank=True)
    
    # Shared fields
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    rating = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    review = models.TextField(null=True, blank=True)

    # Delivery-specific fields
    load_image = models.ImageField(upload_to='job_loads/%Y/%m/%d/', null=True, blank=True)
    is_urgent = models.BooleanField(default=False)
    vehicle_type_required = models.CharField(
        max_length=20,
        choices=Vehicle.VEHICLE_TYPES + [('ANY', 'Any Vehicle')],
        default='ANY'
    )

    def calculate_estimated_price(self):
        """Pricing rule: Taxi = E60 for 1-3km + E10/km; Delivery = E80 for 1-3km + E15/km"""
        base_price = 60.0 if self.service_type == 'TAXI' else 80.0
        additional_rate = 10.0 if self.service_type == 'TAXI' else 15.0
        if self.distance_km <= 3:
            return base_price
        return base_price + (self.distance_km - 3) * additional_rate

    def save(self, *args, **kwargs):
        if not self.estimated_price:
            self.estimated_price = self.calculate_estimated_price()
        if self.status == 'COMPLETED' and self.rating and self.provider:
            self.provider.profile.update_rating(self.rating)
        super().save(*args, **kwargs)

    def clean_pickup_time(self):
        if self.pickup_time and self.pickup_time < timezone.now():
            raise ValidationError("Pickup time must be in the future.")
        return self.pickup_time

    def verify_provider(self):
        """Verify if the provider meets requirements"""
        if not self.provider:
            return False
        profile = self.provider.profile
        if profile.account_type != 'PROVIDER' or not profile.is_verified:
            return False
        # Check service type compatibility
        if profile.service_types not in ['BOTH', self.service_type]:
            return False
        # Check vehicle compatibility
        if self.service_type == 'DELIVERY' and self.vehicle_type_required != 'ANY':
            return any(
                v.is_verified and v.vehicle_type == self.vehicle_type_required
                for v in self.provider.vehicles.all()
            )
        return True
    
    class Meta:
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['provider', 'status']),
        ]

    def __str__(self):
        return f"{self.service_type} Job by {self.client.username} - {self.pickup_location} to {self.dropoff_location}"

class TransportBid(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    ]

    transport_job = models.ForeignKey(TransportRequest, on_delete=models.CASCADE, related_name='bids')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bids')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    proposal = models.TextField(null=True, blank=True)
    estimated_completion_time = models.IntegerField(help_text="Estimated time in minutes", null=True, blank=True)
    vehicle_type = models.CharField(
        max_length=20,
        choices=Vehicle.VEHICLE_TYPES + [('ANY', 'Any Vehicle')],
        default='ANY'
    )
    job_sample = models.FileField(upload_to='bid_samples/%Y/%m/%d/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def can_bid(self):
        """Check if provider meets requirements to bid"""
        profile = self.provider.profile
        if profile.account_type != 'PROVIDER' or not profile.is_verified:
            return False
        if profile.service_types not in ['BOTH', self.transport_job.service_type]:
            return False
        if self.transport_job.service_type == 'DELIVERY' and self.vehicle_type != 'ANY':
            return any(
                v.is_verified and v.vehicle_type == self.vehicle_type
                for v in self.provider.vehicles.all()
            )
        return True
    
    def clean_job_sample(self):
        job_sample = self.job_sample
        if job_sample:
            if job_sample.size > 5 * 1024 * 1024:  # 5MB
                raise ValidationError("File size must be under 5MB.")
        return job_sample

    def __str__(self):
        return f"Bid of {self.amount} by {self.provider.username} for {self.transport_job}"

class TransportContract(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    transport_job = models.OneToOneField(TransportRequest, on_delete=models.CASCADE, related_name='contract')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contracts')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='client_contracts')
    agreed_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    terms = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    confirmed_by_provider = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def confirm_contract(self):
        """Provider confirms the contract"""
        if self.transport_job.verify_provider():
            self.confirmed_by_provider = True
            self.status = 'ACTIVE'
            self.transport_job.status = 'ACCEPTED'
            self.transport_job.provider = self.provider
            self.transport_job.save()
            self.save()

    def __str__(self):
        return f"Contract for {self.transport_job} with {self.provider.username}"

class TransportContractTemplate(models.Model):
    SERVICE_TYPE_CHOICES = [
        ('TAXI', 'Taxi'),
        ('DELIVERY', 'Delivery'),
        ('DEFAULT', 'Default'),
    ]

    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES, unique=True, default='DEFAULT')
    terms = models.TextField(
        help_text="Use placeholders: {service_type}, {agreed_amount}, {pickup_location}, {dropoff_location}, {client_name}, {provider_name}, {job_id}"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_service_type_display()} Contract Template"

    class Meta:
        verbose_name = "Transport Contract Template"
        verbose_name_plural = "Transport Contract Templates"

    @classmethod
    def get_template(cls, service_type):
        """Retrieve the active template for the given service type, fallback to DEFAULT."""
        try:
            return cls.objects.get(service_type=service_type, is_active=True)
        except cls.DoesNotExist:
            try:
                return cls.objects.get(service_type='DEFAULT', is_active=True)
            except cls.DoesNotExist:
                return None