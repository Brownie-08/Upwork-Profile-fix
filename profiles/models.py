from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import (
    FileExtensionValidator,
    RegexValidator,
)
import os
import uuid
import random
import string
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=20, blank=True, default="")
    middle_name = models.CharField(max_length=20, blank=True, default="")
    last_name = models.CharField(max_length=20, blank=True, default="")
    bio = models.TextField(max_length=500, blank=True, default="")
    profile_picture = models.ImageField(
        upload_to="profile_pics/user.username", default="default.jpg"
    )
    skills = models.CharField(max_length=200, blank=True, default="")
    portfolio_link = models.URLField(blank=True)
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    phone_regex = RegexValidator(
        regex=r"^\+268\d{7,8}$",
        message="Phone number must be in Eswatini format: '+268 7XXX XXXX' or '+268 2XXX XXXX'.",
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)

    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Professional title, e.g. 'Transport Service Provider'",
    )
    location = models.CharField(max_length=200, blank=True)
    languages = models.CharField(
        max_length=200, blank=True, help_text="Languages spoken, comma separated"
    )
    linkedin_profile = models.URLField(blank=True)
    github_profile = models.URLField(blank=True)

    years_of_experience = models.PositiveIntegerField(default=0)
    total_projects = models.PositiveIntegerField(default=0)
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    preferred_project_size = models.CharField(
        max_length=20,
        choices=[
            ("SMALL", "Small"),
            ("MEDIUM", "Medium"),
            ("LARGE", "Large"),
            ("ANY", "Any Size"),
        ],
        default="ANY",
    )
    gender = models.CharField(
        max_length=15,
        choices=[("M", "Male"), ("F", "Female"), ("O", "Other")],
        default="O",
    )

    ACCOUNT_TYPES = [
        ("REGULAR", "Regular User"),
        ("TRANSPORT", "Transport Service Provider"),
    ]
    account_type = models.CharField(
        max_length=10, choices=ACCOUNT_TYPES, default="REGULAR"
    )

    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.PositiveIntegerField(default=0)

    # Transport Owner Tag - computed based on document approvals and operator assignments
    transport_owner_tag = models.BooleanField(
        default=False,
        help_text="True if user qualifies as a Transport Owner based on document approvals",
    )

    def __str__(self):
        return f"{self.user.username} Profile"

    def calculate_success_rate(self):
        """Calculate the success rate based on completed projects and reviews."""
        completed_projects = self.user.freelancer_projects.filter(
            status="COMPLETED"
        ).count()
        total_projects = self.user.freelancer_projects.exclude(status="OPEN").count()
        if total_projects > 0:
            self.success_rate = (completed_projects / total_projects) * 100
            self.save()

    def update_total_projects(self):
        """Update the total number of completed projects."""
        self.total_projects = self.user.freelancer_projects.filter(
            status="COMPLETED"
        ).count()
        self.save()

    def get_full_name(self):
        return f"{self.first_name} {self.middle_name} {self.last_name}".strip()

    def get_average_rating(self):
        """Calculate the average rating from all reviews."""
        reviews = self.user.reviews_received.all()
        if reviews:
            return sum(review.rating for review in reviews) / reviews.count()
        return 0

    @property
    def is_identity_verified(self):
        """Check if identity verification is complete using DocumentReview system."""
        try:
            # Check if all three identity document types are approved
            required_doc_types = ["ID_CARD", "FACE_PHOTO", "PROOF_OF_RESIDENCE"]

            for doc_type in required_doc_types:
                try:
                    document = Document.objects.get(user=self.user, doc_type=doc_type)
                    if (
                        not hasattr(document, "review")
                        or document.review.status != "APPROVED"
                    ):
                        return False
                except Document.DoesNotExist:
                    return False

            return True
        except Exception as e:
            logger.error(
                f"Error checking identity verification for {self.user.username}: {str(e)}"
            )
            return False

    @property
    def is_vehicle_verified(self):
        """Check if user owns or is an operator of at least one verified vehicle with verified documents."""
        return (
            self.vehicles.filter(is_verified=True).exists()
            or self.user.operated_vehicles.filter(
                is_verified=True,
                operator_documents__drivers_license_verified=True,
                operator_documents__user=self.user,
            ).exists()
        )

    @property
    def is_permit_verified(self):
        """Check if a valid government permit is verified for TRANSPORT accounts."""
        if self.account_type == "TRANSPORT":
            return self.government_permits.filter(is_verified=True).exists()
        return False

    @property
    def has_verified_drivers_license(self):
        """Check if user has a verified driver's license."""
        return OperatorDocument.objects.filter(
            user=self.user, drivers_license_verified=True
        ).exists()

    def update_rating(self, new_rating):
        """Update average rating when a new review is submitted."""
        self.total_reviews += 1
        self.average_rating = (
            (self.average_rating * (self.total_reviews - 1)) + new_rating
        ) / self.total_reviews
        self.save()

    def update_transport_owner_tag(self):
        """
        Update Transport Owner Tag based on document approvals and operator assignments.

        Criteria for Transport Owner tag:
        1. Roadworthy Certificate (APPROVED)
        2. Blue Book (APPROVED)
        3. Driver's License (APPROVED) - uploaded by owner or assigned operator

        Tag is automatically recalculated when:
        - Document review status changes
        - Operator assignment is created/removed
        """
        try:
            # Get all owned vehicles
            owned_vehicles = self.user.owned_vehicles.all()

            if not owned_vehicles.exists():
                self.transport_owner_tag = False
                self.save(update_fields=["transport_owner_tag"])
                return False

            # Check if at least one vehicle meets all criteria
            for vehicle in owned_vehicles:
                has_roadworthy = (
                    self._check_document_status(vehicle, "ROADWORTHY") == "APPROVED"
                )
                has_bluebook = (
                    self._check_document_status(vehicle, "BLUEBOOK") == "APPROVED"
                )
                has_driver_license = (
                    self._check_driver_license_status(vehicle) == "APPROVED"
                )

                # All three documents must be approved for this vehicle
                if has_roadworthy and has_bluebook and has_driver_license:
                    self.transport_owner_tag = True
                    self.save(update_fields=["transport_owner_tag"])
                    logger.info(f"Transport Owner tag enabled for {self.user.username}")
                    return True

            # If no vehicle meets all criteria, remove the tag
            self.transport_owner_tag = False
            self.save(update_fields=["transport_owner_tag"])
            logger.info(f"Transport Owner tag disabled for {self.user.username}")
            return False

        except Exception as e:
            logger.error(
                f"Error updating transport owner tag for {self.user.username}: {str(e)}"
            )
            return False

    def _check_document_status(self, vehicle, doc_type):
        """Check the approval status of a specific document type for a vehicle"""
        try:
            from .models import Document  # Import here to avoid circular imports

            document = Document.objects.get(
                user=self.user, vehicle=vehicle, doc_type=doc_type
            )
            return document.review.status if hasattr(document, "review") else "PENDING"
        except Document.DoesNotExist:
            return "MISSING"
        except Exception:
            return "MISSING"

    def _check_driver_license_status(self, vehicle):
        """
        Check driver's license status for a vehicle.
        Can be approved either by:
        1. Owner uploading their own driver's license for the vehicle
        2. Assigned operator uploading their driver's license
        """
        try:
            from .models import (
                Document,
                OperatorAssignment,
            )  # Import here to avoid circular imports

            # Check if owner has uploaded and got approved driver's license for this vehicle
            try:
                owner_license = Document.objects.get(
                    user=self.user, vehicle=vehicle, doc_type="DRIVER_LICENSE"
                )
                if (
                    hasattr(owner_license, "review")
                    and owner_license.review.status == "APPROVED"
                ):
                    return "APPROVED"
            except Document.DoesNotExist:
                pass

            # Check if vehicle has an active operator with approved driver's license
            try:
                assignment = OperatorAssignment.objects.get(
                    vehicle=vehicle, active=True
                )
                operator_license = Document.objects.get(
                    user=assignment.operator, vehicle=vehicle, doc_type="DRIVER_LICENSE"
                )
                if (
                    hasattr(operator_license, "review")
                    and operator_license.review.status == "APPROVED"
                ):
                    return "APPROVED"
            except (OperatorAssignment.DoesNotExist, Document.DoesNotExist):
                pass

            # Check for user-only driver's license (no vehicle specified)
            try:
                user_license = Document.objects.get(
                    user=self.user,
                    vehicle=None,  # User-only document
                    doc_type="DRIVER_LICENSE",
                )
                if (
                    hasattr(user_license, "review")
                    and user_license.review.status == "APPROVED"
                ):
                    return "APPROVED"
            except Document.DoesNotExist:
                pass

            return "MISSING"

        except Exception as e:
            logger.error(f"Error checking driver license status: {str(e)}")
            return "MISSING"


def identity_verification_file_path(instance, filename):
    """Generate a custom file path for identity verification documents."""
    ext = os.path.splitext(filename)[1].lower().lstrip(".")  # e.g., 'jpg'
    unique_name = f"{uuid.uuid4()}.{ext}"
    for field_name in ["id_card", "face_photo", "proof_of_residence"]:
        if (
            getattr(instance, field_name)
            and getattr(instance, field_name).name == filename
        ):
            doc_type = field_name
            break
    else:
        doc_type = "other"
    return f"verification_docs/user_{instance.profile.user.id}/{doc_type}/{unique_name}"


def vehicle_file_path(instance, filename):
    """Generate a custom file path for vehicle documents."""
    ext = os.path.splitext(filename)[1].lower().lstrip(".")  # e.g., 'pdf'
    unique_name = f"{uuid.uuid4()}.{ext}"
    for field_name in [
        "drivers_license",
        "blue_book",
        "inspection_certificate",
        "insurance",
    ]:
        if (
            getattr(instance, field_name)
            and getattr(instance, field_name).name == filename
        ):
            doc_type = field_name
            break
    else:
        doc_type = "other"
    return (
        f"vehicle_docs/user_{instance.vehicle.profile.user.id}/{doc_type}/{unique_name}"
    )


def permit_file_path(instance, filename):
    """Generate a custom file path for government permits."""
    ext = os.path.splitext(filename)[1].lower().lstrip(".")  # e.g., 'pdf'
    unique_name = f"{uuid.uuid4()}.{ext}"
    return f"permit_docs/user_{instance.profile.user.id}/psv_permit/{unique_name}"


def operator_document_file_path(instance, filename):
    """Generate a custom file path for operator documents."""
    ext = os.path.splitext(filename)[1].lower().lstrip(".")  # e.g., 'pdf'
    unique_name = f"{uuid.uuid4()}.{ext}"
    return f"operator_docs/user_{instance.user.id}/drivers_license/{unique_name}"


class IdentityVerification(models.Model):
    profile = models.OneToOneField(
        "Profile", on_delete=models.CASCADE, related_name="identity_verification"
    )

    id_card = models.FileField(
        upload_to=identity_verification_file_path,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "pdf"])
        ],
    )
    id_card_verified = models.BooleanField(default=False)
    id_card_verified_at = models.DateTimeField(null=True, blank=True)
    id_card_verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="verified_id_cards"
    )
    id_card_rejection_reason = models.TextField(blank=True, null=True)

    face_photo = models.FileField(
        upload_to=identity_verification_file_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])],
    )
    face_photo_verified = models.BooleanField(default=False)
    face_photo_verified_at = models.DateTimeField(null=True, blank=True)
    face_photo_verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="verified_face_photos"
    )
    face_photo_rejection_reason = models.TextField(blank=True, null=True)

    proof_of_residence = models.FileField(
        upload_to=identity_verification_file_path,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "pdf"])
        ],
    )
    proof_of_residence_verified = models.BooleanField(default=False)
    proof_of_residence_verified_at = models.DateTimeField(null=True, blank=True)
    proof_of_residence_verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="verified_proofs_of_residence",
    )
    proof_of_residence_rejection_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Identity Verification for {self.profile.user.username}"

    def save(self, *args, **kwargs):
        for field in ["id_card", "face_photo", "proof_of_residence"]:
            verified_by = getattr(self, f"{field}_verified_by")
            verified = getattr(self, f"{field}_verified")
            if verified_by and not verified:
                setattr(self, f"{field}_verified", True)
                setattr(self, f"{field}_verified_at", timezone.now())
                setattr(self, f"{field}_rejection_reason", None)
            elif not verified_by and verified:
                setattr(self, f"{field}_verified", False)
                setattr(self, f"{field}_verified_at", None)
                setattr(self, f"{field}_rejection_reason", None)
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "id_card_verified",
                    "face_photo_verified",
                    "proof_of_residence_verified",
                ]
            ),
        ]


class Vehicle(models.Model):
    profile = models.ForeignKey(
        "Profile", on_delete=models.CASCADE, related_name="vehicles"
    )
    operators = models.ManyToManyField(
        User, related_name="operated_vehicles", blank=True
    )

    VEHICLE_TYPES = [
        ("CAR", "Car"),
        ("VAN", "Van"),
        ("TRUCK", "Truck"),
        ("MOTORCYCLE", "Motorcycle"),
        ("TAXI", "Taxi"),
        ("DELIVERY", "Delivery Vehicle"),
    ]
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveIntegerField()
    license_plate = models.CharField(
        max_length=10,
        validators=[
            RegexValidator(
                regex=r"^[A-Z]SD\s\d{3}\s[A-Z]{2}$",
                message="License plate must follow Eswatini format (e.g., JSD 123 AM)",
            )
        ],
        unique=True,
    )

    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    last_inspection_date = models.DateField(null=True, blank=True)
    next_inspection_date = models.DateField(null=True, blank=True)

    def is_inspection_valid(self):
        if self.next_inspection_date:
            return datetime.now().date() <= self.next_inspection_date
        return False

    def days_until_inspection(self):
        if self.next_inspection_date:
            return (self.next_inspection_date - datetime.now().date()).days
        return 0

    def __str__(self):
        return f"{self.year} {self.make} {self.model} ({self.license_plate})"

    def save(self, *args, **kwargs):
        logger.debug(
            f"Saving Vehicle: license_plate={self.license_plate}, pk={self.pk}, is_verified={self.is_verified}"
        )
        original_is_verified = self.is_verified
        super().save(*args, **kwargs)
        logger.debug(f"Vehicle saved: pk={self.pk}, is_verified={self.is_verified}")
        document = self.documents.first()
        logger.debug(f"Document found: {document}")
        self.is_verified = False
        if document:
            drivers_license_ok = (
                document.drivers_license_verified
                or OperatorDocument.objects.filter(
                    vehicle=self, drivers_license_verified=True
                ).exists()
            )
            self.is_verified = (
                document.blue_book_verified
                and document.inspection_certificate_verified
                and (document.insurance_verified if document.insurance else True)
                and drivers_license_ok
            )
        if self.is_verified != original_is_verified:
            logger.debug(
                f"is_verified changed from {original_is_verified} to {self.is_verified}"
            )
            super().save(update_fields=["is_verified"])
        if self.is_verified:
            if self.profile.account_type != "TRANSPORT":
                logger.debug(f"Updating profile {self.profile} to TRANSPORT")
                self.profile.account_type = "TRANSPORT"
                self.profile.save()
            for operator in self.operators.all():
                if OperatorDocument.objects.filter(
                    user=operator, vehicle=self, drivers_license_verified=True
                ).exists():
                    if operator.profile.account_type != "TRANSPORT":
                        logger.debug(
                            f"Updating operator {operator} profile to TRANSPORT"
                        )
                        operator.profile.account_type = "TRANSPORT"
                        operator.profile.save()

    class Meta:
        indexes = [
            models.Index(fields=["license_plate"]),
            models.Index(fields=["is_active", "is_verified"]),
        ]


class VehicleDocument(models.Model):
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="documents"
    )

    drivers_license = models.FileField(
        upload_to=vehicle_file_path,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "pdf"])
        ],
    )
    drivers_license_verified = models.BooleanField(default=False)
    drivers_license_verified_at = models.DateTimeField(null=True, blank=True)
    drivers_license_verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="verified_drivers_licenses",
    )
    drivers_license_rejection_reason = models.TextField(blank=True, null=True)

    blue_book = models.FileField(
        upload_to=vehicle_file_path,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "pdf"])
        ],
    )
    blue_book_verified = models.BooleanField(default=False)
    blue_book_verified_at = models.DateTimeField(null=True, blank=True)
    blue_book_verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="verified_blue_books"
    )
    blue_book_rejection_reason = models.TextField(blank=True, null=True)

    inspection_certificate = models.FileField(
        upload_to=vehicle_file_path,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "pdf"])
        ],
    )
    inspection_certificate_verified = models.BooleanField(default=False)
    inspection_certificate_verified_at = models.DateTimeField(null=True, blank=True)
    inspection_certificate_verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="verified_inspection_certificates",
    )
    inspection_certificate_rejection_reason = models.TextField(blank=True, null=True)

    insurance = models.FileField(
        upload_to=vehicle_file_path,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "pdf"])
        ],
    )
    insurance_verified = models.BooleanField(default=False)
    insurance_verified_at = models.DateTimeField(null=True, blank=True)
    insurance_verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="verified_insurances"
    )
    insurance_rejection_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Documents for {self.vehicle}"

    def save(self, *args, **kwargs):
        for field in [
            "drivers_license",
            "blue_book",
            "inspection_certificate",
            "insurance",
        ]:
            verified_by = getattr(self, f"{field}_verified_by")
            verified = getattr(self, f"{field}_verified")
            if verified_by and not verified:
                setattr(self, f"{field}_verified", True)
                setattr(self, f"{field}_verified_at", timezone.now())
                setattr(self, f"{field}_rejection_reason", None)
            elif not verified_by and verified:
                setattr(self, f"{field}_verified", False)
                setattr(self, f"{field}_verified_at", None)
                setattr(self, f"{field}_rejection_reason", None)
        super().save(*args, **kwargs)
        self.vehicle.save()  # Update vehicle.is_verified

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "drivers_license_verified",
                    "blue_book_verified",
                    "inspection_certificate_verified",
                    "insurance_verified",
                ]
            ),
        ]


class OperatorDocument(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="operator_documents"
    )
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="operator_documents"
    )
    drivers_license = models.FileField(
        upload_to=operator_document_file_path,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "pdf"])
        ],
    )
    drivers_license_verified = models.BooleanField(default=False)
    drivers_license_verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="operator_license_verified",
    )
    drivers_license_verified_at = models.DateTimeField(null=True, blank=True)
    drivers_license_rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Driver’s License for {self.user.username} (Vehicle: {self.vehicle.license_plate})"

    def save(self, *args, **kwargs):
        if self.drivers_license_verified_by and not self.drivers_license_verified:
            self.drivers_license_verified = True
            self.drivers_license_verified_at = timezone.now()
            self.drivers_license_rejection_reason = None
        elif not self.drivers_license_verified_by and self.drivers_license_verified:
            self.drivers_license_verified = False
            self.drivers_license_verified_at = None
            self.drivers_license_rejection_reason = None
        super().save(*args, **kwargs)
        self.vehicle.save()  # Update vehicle.is_verified

    class Meta:
        indexes = [
            models.Index(fields=["drivers_license_verified"]),
            models.Index(fields=["user", "vehicle"]),
        ]
        unique_together = ("user", "vehicle")


class GovernmentPermit(models.Model):
    profile = models.ForeignKey(
        "Profile", on_delete=models.CASCADE, related_name="government_permits"
    )
    permit_type = models.CharField(
        max_length=20,
        choices=[
            ("TAXI", "Taxi PSV Permit"),
            ("DELIVERY", "Delivery PSV Permit"),
            ("TRANSPORT", "Government Permit"),
        ],
    )
    permit_document = models.FileField(
        upload_to=permit_file_path,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "pdf"])
        ],
    )
    permit_number = models.CharField(max_length=50, unique=True)
    issue_date = models.DateField()
    expiry_date = models.DateField()
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="verified_permits"
    )
    rejection_reason = models.TextField(blank=True, null=True)

    def is_valid(self):
        return datetime.now().date() <= self.expiry_date

    def days_until_expiry(self):
        if self.expiry_date:
            return (self.expiry_date - datetime.now().date()).days
        return 0

    def __str__(self):
        return f"{self.get_permit_type_display()} for {self.profile.user.username}"

    def save(self, *args, **kwargs):
        if self.verified_by and not self.is_verified:
            self.is_verified = True
            self.verified_at = timezone.now()
            self.rejection_reason = None
        elif not self.verified_by and self.is_verified:
            self.is_verified = False
            self.verified_at = None
            self.rejection_reason = None
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=["permit_type", "is_verified"]),
            models.Index(fields=["permit_number"]),
        ]


class Experience(models.Model):
    profile = models.ForeignKey(
        "Profile", on_delete=models.CASCADE, related_name="experiences"
    )
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    current = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField()

    def __str__(self):
        return f"{self.title} at {self.company}"


class Education(models.Model):
    profile = models.ForeignKey(
        "Profile", on_delete=models.CASCADE, related_name="education"
    )
    institution = models.CharField(max_length=200)
    degree = models.CharField(max_length=200)
    field_of_study = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    current = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Education"

    def __str__(self):
        return f"{self.degree} in {self.field_of_study} from {self.institution}"


def portfolio_file_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    unique_name = f"{uuid.uuid4()}.{ext}"
    user_id = (
        instance.user.id
        if isinstance(instance, Portfolio)
        else instance.portfolio.user.id
    )
    media_type = {
        "jpg": "images",
        "jpeg": "images",
        "png": "images",
        "gif": "images",
        "bmp": "images",
        "webp": "images",
        "mp4": "videos",
        "mov": "videos",
        "avi": "videos",
        "mkv": "videos",
        "mp3": "audio",
        "wav": "audio",
        "aac": "audio",
        "pdf": "pdfs",
    }.get(ext, "other")
    return f"portfolio/user_{user_id}/{media_type}/{unique_name}"


class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    completion_date = models.DateField()
    title = models.CharField(max_length=70)
    role = models.CharField(max_length=100, blank=True)
    description = models.TextField(max_length=600)
    skills = models.CharField(
        max_length=200,
        default="None",
        help_text="Comma-separated list of skills used in the project",
    )
    related_job = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to=portfolio_file_path, blank=True, null=True)
    sample = models.ForeignKey(
        "PortfolioSample",
        on_delete=models.CASCADE,
        null=True,
        related_name="sample_instance",
    )

    def __str__(self):
        return self.title


class PortfolioSample(models.Model):
    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name="portfolio_samples"
    )
    video = models.FileField(upload_to=portfolio_file_path, blank=True, null=True)
    audio = models.FileField(upload_to=portfolio_file_path, blank=True, null=True)
    pdf = models.FileField(upload_to=portfolio_file_path, blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    text_block = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Samples for {self.portfolio.title}"


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class ProfileSkill(models.Model):
    PROFICIENCY_CHOICES = [
        ("BEG", "Beginner"),
        ("INT", "Intermediate"),
        ("ADV", "Advanced"),
        ("EXP", "Expert"),
    ]

    profile = models.ForeignKey(
        "Profile", on_delete=models.CASCADE, related_name="profile_skills"
    )
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    proficiency = models.CharField(max_length=3, choices=PROFICIENCY_CHOICES)
    verified = models.BooleanField(default=False)
    years_of_experience = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("profile", "skill")

    def __str__(self):
        return f"{self.skill.name} - {self.get_proficiency_display()}"


class Availability(models.Model):
    profile = models.OneToOneField(
        "Profile", on_delete=models.CASCADE, related_name="availability"
    )
    available_for_work = models.BooleanField(default=True)
    hours_per_week = models.PositiveIntegerField(default=40)
    preferred_contract_type = models.CharField(
        max_length=20,
        choices=[
            ("FULL_TIME", "Full Time"),
            ("PART_TIME", "Part Time"),
            ("CONTRACT", "Contract"),
            ("HOURLY", "Hourly"),
        ],
        default="FULL_TIME",
    )
    notice_period = models.PositiveIntegerField(
        default=7, help_text="Notice period in days"
    )

    def __str__(self):
        return f"{self.profile.user.username}'s Availability"


class LoginOTP(models.Model):
    PURPOSE_CHOICES = [
        ("VERIFY", "Account Verification"),
        ("RESET", "Password Reset"),
    ]

    CHANNEL_CHOICES = [
        ("EMAIL", "Email"),
        ("SMS", "SMS"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="login_otps")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=10, choices=PURPOSE_CHOICES)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["user", "purpose", "verified"]),
            models.Index(fields=["expires_at"]),
        ]
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.pk:  # Only on creation
            if not self.code:
                self.code = self.generate_code()
            if not self.expires_at:
                self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    @staticmethod
    def generate_code():
        """Generate a 6-digit numeric OTP code"""
        return "".join([str(random.randint(0, 9)) for _ in range(6)])

    def is_expired(self):
        """Check if the OTP has expired"""
        return timezone.now() > self.expires_at

    def is_valid(self):
        """Check if OTP is valid (not expired, not verified, attempts < 5)"""
        return not self.is_expired() and not self.verified and self.attempts < 5

    def __str__(self):
        return (
            f"OTP {self.code} for {self.user.username} ({self.get_purpose_display()})"
        )


class Referral(models.Model):
    """User referral system model"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="referral")
    code = models.CharField(
        max_length=10, unique=True, help_text="Unique referral code for this user"
    )
    referred_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referred_users",
        help_text="The user who referred this user",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["referred_by"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        """Auto-generate referral code if not set"""
        if not self.code:
            from .services.referral import ReferralService

            # Keep trying until we get a unique code
            max_attempts = 10
            attempts = 0
            while attempts < max_attempts:
                code = ReferralService.generate_code()
                if not Referral.objects.filter(code=code).exists():
                    self.code = code
                    break
                attempts += 1

            # If we still don't have a code, use timestamp fallback
            if not self.code:
                import time

                timestamp = str(int(time.time()))[-4:]
                self.code = (
                    "".join([c for c in ReferralService.generate_code()[:4]])
                    + timestamp
                )

        super().save(*args, **kwargs)

    @property
    def total_referrals(self):
        """Get total number of users referred by this user"""
        return self.user.referred_users.count()

    def __str__(self):
        return f"Referral code {self.code} for {self.user.username}"


def document_file_path(instance, filename):
    """Generate a custom file path for document uploads."""
    ext = os.path.splitext(filename)[1].lower().lstrip(".")  # e.g., 'pdf'
    unique_name = f"{uuid.uuid4()}.{ext}"
    doc_type = instance.doc_type.lower()
    user_id = instance.user.id
    vehicle_part = f"vehicle_{instance.vehicle.id}/" if instance.vehicle else ""
    return f"documents/user_{user_id}/{vehicle_part}{doc_type}/{unique_name}"


class Document(models.Model):
    """Generic document model for vehicle and user documents"""

    DOC_TYPE_CHOICES = [
        ("ROADWORTHY", "Roadworthiness Certificate"),
        ("BLUEBOOK", "Registration Certificate (Blue Book)"),
        ("DRIVER_LICENSE", "Driver's License"),
        ("PERMIT", "PSV Permit"),
        ("ID_CARD", "Government ID Card"),
        ("FACE_PHOTO", "Face Photo"),
        ("PROOF_OF_RESIDENCE", "Proof of Residence"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    vehicle = models.ForeignKey(
        "VehicleOwnership",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="generic_documents",
        help_text="Leave blank for user-only documents like driver's license",
    )
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    file = models.FileField(
        upload_to=document_file_path,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "pdf"])
        ],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "doc_type"]),
            models.Index(fields=["vehicle", "doc_type"]),
            models.Index(fields=["uploaded_at"]),
        ]
        unique_together = [["user", "vehicle", "doc_type"]]

    def __str__(self):
        vehicle_info = f" for {self.vehicle.plate_number}" if self.vehicle else ""
        return f"{self.get_doc_type_display()}{vehicle_info} - {self.user.username}"


class DocumentReview(models.Model):
    """Document review and approval workflow"""

    STATUS_CHOICES = [
        ("PENDING", "Pending Review"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name="review"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    reason = models.TextField(
        blank=True, help_text="Required when rejecting a document"
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_documents",
        help_text="Admin user who reviewed this document",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["reviewed_at"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        """Auto-set reviewed_at when status changes and trigger notifications"""
        if self.pk:  # Existing record
            old_review = DocumentReview.objects.get(pk=self.pk)
            if old_review.status != self.status and self.status in [
                "APPROVED",
                "REJECTED",
            ]:
                self.reviewed_at = timezone.now()
                if not self.reviewed_by:
                    # If reviewed_by is not set, we need it for audit trail
                    logger.warning(
                        f"Document review status changed without reviewer: {self}"
                    )
        elif self.status in ["APPROVED", "REJECTED"]:
            self.reviewed_at = timezone.now()

        super().save(*args, **kwargs)

        # Trigger notifications after save
        if self.status in ["APPROVED", "REJECTED"] and self.reviewed_at:
            self._send_notification()

            # Handle PERMIT document approvals/rejections
            if self.document.doc_type == "PERMIT":
                self._handle_permit_review()

            # Trigger Transport Owner Tag recalculation when document status changes
            try:
                # Update tag for document owner
                self.document.user.profile.update_transport_owner_tag()

                # If this is a vehicle document, also update the vehicle owner's tag
                if self.document.vehicle:
                    self.document.vehicle.owner.profile.update_transport_owner_tag()

            except Exception as e:
                logger.error(
                    f"Error updating transport owner tag after document review: {str(e)}"
                )

    def _send_notification(self):
        """Send notification to document owner about review decision"""
        try:
            from notifications.models import Notification

            if self.status == "APPROVED":
                if self.document.doc_type == "PERMIT":
                    message = "Your Government Permit has been approved. You are now an Authorized Provider."
                else:
                    message = f"Your {self.document.get_doc_type_display()} has been approved."
            else:  # REJECTED
                reason_text = f" Reason: {self.reason}" if self.reason else ""
                if self.document.doc_type == "PERMIT":
                    message = f"Permit rejected.{reason_text} Please re-upload."
                else:
                    message = f"Your {self.document.get_doc_type_display()} was rejected.{reason_text}"

            # Create in-app notification
            Notification.objects.create(user=self.document.user, message=message)

            logger.info(
                f"Notification sent to {self.document.user.username} for document {self.document.id}"
            )

            # TODO: Add email/SMS notification integration here

        except Exception as e:
            logger.error(
                f"Failed to send notification for document review {self.id}: {str(e)}"
            )

    def _handle_permit_review(self):
        """Handle permit approval/rejection and update TransportOwnerBadge"""
        try:
            # Get or create the transport badge for this user
            badge, created = TransportOwnerBadge.objects.get_or_create(
                user=self.document.user, defaults={"authorized": False}
            )

            if self.status == "APPROVED":
                # Approve the badge
                badge.authorized = True
                badge.save()
                logger.info(
                    f"TransportOwnerBadge authorized for {self.document.user.username}"
                )
            elif self.status == "REJECTED":
                # Remove authorization
                badge.authorized = False
                badge.save()
                logger.info(
                    f"TransportOwnerBadge authorization removed for {self.document.user.username}"
                )

        except Exception as e:
            logger.error(
                f"Error handling permit review for user {self.document.user.username}: {str(e)}"
            )

    def __str__(self):
        return f"{self.document} - {self.get_status_display()}"


class VehicleOwnership(models.Model):
    """New simplified vehicle model for the dashboard workflow"""

    VEHICLE_TYPES = [
        ("CAR", "Car"),
        ("VAN", "Van"),
        ("TRUCK", "Truck"),
        ("MOTORCYCLE", "Motorcycle"),
        ("TAXI", "Taxi"),
        ("DELIVERY", "Delivery Vehicle"),
    ]

    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_vehicles"
    )
    plate_number = models.CharField(
        max_length=15,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[A-Z]SD\s\d{3}\s[A-Z]{2}$",
                message="License plate must follow Eswatini format (e.g., JSD 123 AM)",
            )
        ],
        help_text="License plate in Eswatini format",
    )
    make = models.CharField(max_length=50, blank=True)
    model = models.CharField(max_length=50, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner"]),
            models.Index(fields=["plate_number"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def get_required_documents(self):
        """Get list of required document types for this vehicle"""
        return ["ROADWORTHY", "BLUEBOOK"]

    def get_document_status(self, doc_type):
        """Get the review status for a specific document type"""
        try:
            document = self.generic_documents.get(doc_type=doc_type)
            return document.review.status if hasattr(document, "review") else "PENDING"
        except Document.DoesNotExist:
            return "MISSING"

    def is_fully_documented(self):
        """Check if all required documents are approved"""
        required_docs = self.get_required_documents()
        for doc_type in required_docs:
            if self.get_document_status(doc_type) != "APPROVED":
                return False
        return True

    def __str__(self):
        vehicle_info = (
            f"{self.year} {self.make} {self.model}" if self.make else "Vehicle"
        )
        return f"{vehicle_info} ({self.plate_number})"


class TransportOwnerBadge(models.Model):
    """Badge model for authorized transport providers"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="transport_badge"
    )
    authorized = models.BooleanField(
        default=False, help_text="Whether user is authorized as a transport provider"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["authorized"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        status = "Authorized" if self.authorized else "Not Authorized"
        return f"{self.user.username} - {status}"


class OperatorAssignment(models.Model):
    """Operator assignment system for vehicle owners to assign drivers"""

    vehicle = models.OneToOneField(
        VehicleOwnership,
        on_delete=models.CASCADE,
        related_name="operator_assignment",
        help_text="Vehicle being assigned to an operator",
    )
    operator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assigned_vehicles",
        help_text="User assigned as operator for this vehicle",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assigned_operators",
        help_text="Vehicle owner who made the assignment",
    )
    active = models.BooleanField(
        default=True, help_text="Whether this assignment is currently active"
    )
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["vehicle", "active"]),
            models.Index(fields=["operator", "active"]),
            models.Index(fields=["assigned_at"]),
        ]
        # Ensure only one active operator per vehicle
        constraints = [
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=models.Q(active=True),
                name="one_active_operator_per_vehicle",
            )
        ]
        ordering = ["-assigned_at"]

    def deactivate(self):
        """Deactivate this operator assignment"""
        self.active = False
        self.deactivated_at = timezone.now()
        self.save()

        # Trigger Transport Owner Tag recalculation
        self.vehicle.owner.profile.update_transport_owner_tag()

    def save(self, *args, **kwargs):
        # Ensure assigned_by is set to vehicle owner if not specified
        if not self.assigned_by_id:
            self.assigned_by = self.vehicle.owner

        super().save(*args, **kwargs)

        # Trigger Transport Owner Tag recalculation when assignment changes
        if self.active:
            self.vehicle.owner.profile.update_transport_owner_tag()

    def __str__(self):
        status = "Active" if self.active else "Inactive"
        return f"{self.operator.username} → {self.vehicle.plate_number} ({status})"
