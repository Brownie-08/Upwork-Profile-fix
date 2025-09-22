from django.db import models
from django.contrib.auth.models import User
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    FileExtensionValidator,
)
from django.urls import reverse
import os
from wallets.models import LusitoAccount, ProjectFund


class Project(models.Model):
    STATUS_CHOICES = [
        ("DISCUSSION", "In Discussion"),  # New initial state
        ("OPEN", "Open"),
        ("IN_PROGRESS", "In Progress"),
        ("REVIEW", "Under Review"),
        ("COMPLETED", "Completed"),
        ("DISPUTED", "Disputed"),
    ]

    SERVICE_TYPE_CHOICES = [
        ("WEB_DEVELOPMENT", "Web Development"),
        ("GRAPHIC_DESIGN", "Graphic Design"),
        ("CONTENT_WRITING", "Content Writing"),
        ("MARKETING", "Marketing"),
        ("HOMEWORK", "Homework"),
        ("MOBILE_APP_DEV", "Mobile App Development"),
        ("DATA_ANALYSIS", "Data Analysis"),
        ("TAXI", "Taxi Service"),
        ("OTHER", "Other"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("FIXED", "Fixed Price"),
        ("HOURLY", "Hourly Rate"),
        ("MILESTONE", "Milestone Payment"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="client_projects"
    )
    freelancer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="freelancer_projects",
    )
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="OPEN")
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateField()
    completion_date = models.DateField(null=True, blank=True)
    client_confirmed = models.BooleanField(default=False)
    freelancer_confirmed = models.BooleanField(default=False)
    final_payment = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    rating = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    service_type = models.CharField(
        max_length=50,
        choices=SERVICE_TYPE_CHOICES,
        default="OTHER",
        help_text="Specify the type of service this project falls under",
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="FIXED",
        help_text="Specify the payment method for this project",
    )
    project_files = models.FileField(
        upload_to="project_files/",
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "doc", "docx", "txt", "png", "jpg", "jpeg"]
            )
        ],
        help_text="Upload related files for the project",
    )

    max_file_size = models.PositiveIntegerField(
        default=5242880, help_text="Maximum file size allowed in bytes"  # 5MB in bytes
    )
    allowed_file_types = models.CharField(
        max_length=200,
        default="pdf,doc,docx,txt,png,jpg,jpeg",
        help_text="Comma-separated list of allowed file extensions",
    )

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("project-detail", kwargs={"pk": self.pk})

    def get_allowed_file_types_list(self):
        """Return list of allowed file types"""
        return [ft.strip() for ft in self.allowed_file_types.split(",")]

    def validate_file(self, file):
        """Validate file size and type"""
        if file.size > self.max_file_size:
            raise ValueError(
                f"File size exceeds maximum allowed size of {self.max_file_size/1024/1024}MB"
            )

        file_extension = file.name.split(".")[-1].lower() if "." in file.name else ""
        if file_extension not in self.get_allowed_file_types_list():
            raise ValueError(f"File type '.{file_extension}' is not allowed")

    @property
    def duration(self):
        if self.completion_date and self.start_date:
            return (self.completion_date - self.start_date).days
        return None

    def is_completed(self):
        """
        Returns True if both client and freelancer have confirmed the completion.
        """
        return self.client_confirmed and self.freelancer_confirmed

    def validate_files(self, files):
        """Validate multiple files size and type"""
        for file in files:
            if file.size > self.max_file_size:
                raise ValueError(
                    f"File size exceeds maximum allowed size of {self.max_file_size/1024/1024}MB"
                )

            file_extension = (
                file.name.split(".")[-1].lower() if "." in file.name else ""
            )
            if file_extension not in self.get_allowed_file_types_list():
                raise ValueError(f"File type '.{file_extension}' is not allowed")

    def hold_funds(self):
        """Hold funds when project is created"""
        try:
            site_account = LusitoAccount.objects.first()
            if site_account.hold_project_funds(self.budget):
                ProjectFund.objects.create(
                    project=self, amount=self.budget, commission_rate=0.10
                )
                return True
            return False
        except Exception:
            return False

    def release_funds(self):
        """Release funds if both parties confirm completion"""
        if self.is_completed:
            site_account = LusitoAccount.objects.first()
            if site_account:
                freelancer_payment, commission = site_account.release_project_funds(
                    self.budget, commission_rate=0.10
                )
                if freelancer_payment is not None:
                    # Notify freelancer and client (optional, implement as needed)
                    # Mark project as completed
                    self.status = "COMPLETED"
                    self.save()
                    return freelancer_payment, commission
        return None, None


class ProjectFile(models.Model):
    """Model for storing project-related files"""

    project = models.ForeignKey(
        "Project", on_delete=models.CASCADE, related_name="files"
    )
    file = models.FileField(upload_to="project_files/%Y/%m/%d/")
    file_name = models.CharField(max_length=255, blank=True, null=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    file_type = models.CharField(max_length=100, blank=True, null=True)
    file_size = models.PositiveIntegerField(
        help_text="File size in bytes", blank=True, null=True
    )

    def __str__(self):
        return self.file_name or self.file.name

    def save(self, *args, **kwargs):
        """Override save to set file_name and file_size if not provided"""
        if not self.file_name:
            self.file_name = os.path.basename(
                self.file.name
            )  # Set file_name to filename from path
        if not self.file_size:
            self.file_size = self.file.size  # Automatically set file size (in bytes)
        if not self.file_type:
            self.file_type = (
                self.get_file_type()
            )  # Set file type based on file extension
        super().save(*args, **kwargs)

    def get_file_type(self):
        """Extract file type from filename"""
        return self.file.name.split(".")[-1] if "." in self.file.name else "unknown"

    def get_file_size(self):
        """Return the file size in a human-readable format"""
        size = self.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1048576:
            return f"{size / 1024:.2f} KB"
        elif size < 1073741824:
            return f"{size / 1048576:.2f} MB"
        else:
            return f"{size / 1073741824:.2f} GB"


class ProposalFile(models.Model):
    """Model for storing proposal-related sample work files"""

    proposal = models.ForeignKey(
        "Proposal", on_delete=models.CASCADE, related_name="files"
    )
    file = models.FileField(
        upload_to="proposal_files/%Y/%m/%d/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "pdf",
                    "doc",
                    "docx",
                    "txt",
                    "png",
                    "jpg",
                    "jpeg",
                    "zip",
                ]
            )
        ],
    )
    file_name = models.CharField(max_length=255)
    description = models.TextField(
        blank=True, help_text="Brief description of the sample work"
    )
    upload_date = models.DateTimeField(auto_now_add=True)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")

    def __str__(self):
        return f"Sample work for proposal {self.proposal.id}: {self.file_name}"

    def save(self, *args, **kwargs):
        if not self.file_size and self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)


class Proposal(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="proposals"
    )
    freelancer = models.ForeignKey(User, on_delete=models.CASCADE)
    proposal_text = models.TextField()
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)

    # New fields for file handling
    max_file_size = models.PositiveIntegerField(
        default=10485760,  # 10MB in bytes
        help_text="Maximum file size allowed per file",
    )
    max_files = models.PositiveIntegerField(
        default=5, help_text="Maximum number of files allowed per proposal"
    )

    class Meta:
        unique_together = ("project", "freelancer")

    def __str__(self):
        return f"Proposal for {self.project.title} by {self.freelancer.username}"

    def can_add_more_files(self):
        """Check if more files can be added to the proposal"""
        return self.files.count() < self.max_files


class Review(models.Model):
    """
    Enables clients to review freelancers and vice versa after project completion.
    """

    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    project = models.ForeignKey(
        "Project", on_delete=models.CASCADE, related_name="reviews"
    )
    reviewer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reviews_given"
    )
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reviews_received"
    )
    rating = models.IntegerField(
        choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "reviewer", "recipient")

    def __str__(self):
        return f"Review by {self.reviewer.username} for {self.recipient.username}"


# ratings
class Rating(models.Model):
    RATER_CHOICES = [
        ("CLIENT", "Client"),
        ("FREELANCER", "Freelancer"),
    ]

    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name="ratings"
    )
    rated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="given_ratings"
    )
    rater_type = models.CharField(max_length=10, choices=RATER_CHOICES)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating should be between 1 and 5 stars.",
    )
    comment = models.TextField(
        blank=True, null=True, help_text="Optional comment about the project."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rater_type} Rating for {self.project.title} by {self.rated_by.username}"
