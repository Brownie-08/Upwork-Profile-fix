from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from datetime import date
from django.utils import timezone
import mimetypes
from .models import (
    Profile,
    Experience,
    Education,
    Portfolio,
    PortfolioSample,
    ProfileSkill,
    Skill,
    Availability,
    IdentityVerification,
    Vehicle,
    VehicleDocument,
    GovernmentPermit,
    OperatorDocument,
    VehicleOwnership,
    Document,
    DocumentReview,
    OperatorAssignment,
)
import base64
from django.core.files.base import ContentFile


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        error_messages={"required": "Email is required."},
        widget=forms.EmailInput(attrs={"placeholder": "Enter your email"}),
    )
    first_name = forms.CharField(
        max_length=30, error_messages={"required": "First name is required."}
    )
    last_name = forms.CharField(
        max_length=30, error_messages={"required": "Last name is required."}
    )
    phone_number = forms.CharField(
        max_length=17,
        required=False,
        validators=[
            RegexValidator(
                regex=r"^\+268\d{7,8}$",
                message="Phone number must be in Eswatini format: '+268 7XXX XXXX' or '+268 2XXX XXXX'.",
            )
        ],
        widget=forms.TextInput(attrs={"placeholder": "+268 76000000"}),
        help_text="Optional. Format: +268 7XXX XXXX",
    )
    referral_code = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter referral code (optional)",
                "style": "text-transform: uppercase;",
            }
        ),
        help_text="Optional. Enter a friend's referral code",
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
        ]
        error_messages = {
            "username": {
                "required": "A username is required.",
                "unique": "This username is already taken.",
            },
            "password1": {
                "required": "Please enter a password.",
            },
            "password2": {
                "required": "Please confirm your password.",
            },
        }


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "first_name",
            "middle_name",
            "last_name",
            "title",
            "gender",
            "bio",
            "location",
            "phone_number",
            "languages",
            "hourly_rate",
            "profile_picture",
            "portfolio_link",
            "linkedin_profile",
            "github_profile",
            "preferred_project_size",
            "location",
            "skills",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
            "languages": forms.TextInput(
                attrs={"placeholder": "e.g., SiSwati, English, French"}
            ),
            "phone_number": forms.TextInput(attrs={"placeholder": "+268 76000000"}),
        }


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "first_name",
            "middle_name",
            "last_name",
            "title",
            "bio",
            "location",
            "phone_number",
            "languages",
            "hourly_rate",
            "linkedin_profile",
            "github_profile",
            "profile_picture",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({"class": "form-control"})


class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        fields = [
            "title",
            "company",
            "location",
            "current",
            "start_date",
            "end_date",
            "description",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        current = cleaned_data.get("current")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        # Ensure start_date is provided
        if not start_date:
            raise forms.ValidationError("Start date is required.")

        # Check end_date requirement
        if not current and not end_date:
            raise forms.ValidationError(
                "Please provide an end date or mark as current position."
            )

        # Validate date range if both dates are present
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("End date must be after start date.")

        return cleaned_data


class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = [
            "institution",
            "degree",
            "field_of_study",
            "start_date",
            "end_date",
            "current",
            "description",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = [
            "title",
            "role",
            "description",
            "skills",
            "related_job",
            "completion_date",
            "image",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "skills": forms.TextInput(
                attrs={"placeholder": "e.g., Python, React, Figma"}
            ),
            "completion_date": forms.DateInput(attrs={"type": "date"}),
            "image": forms.FileInput(attrs={"accept": "image/*"}),
        }

    def clean_completion_date(self):
        completion_date = self.cleaned_data.get("completion_date")
        if completion_date and completion_date > timezone.now().date():
            raise forms.ValidationError("Completion date cannot be in the future.")
        return completion_date


class PortfolioSampleForm(forms.ModelForm):
    class Meta:
        model = PortfolioSample
        fields = ["video", "audio", "pdf", "url", "text_block"]
        widgets = {
            "text_block": forms.Textarea(attrs={"rows": 3}),
            "url": forms.URLInput(attrs={"placeholder": "https://example.com"}),
            "video": forms.FileInput(attrs={"accept": "video/*"}),
            "audio": forms.FileInput(attrs={"accept": "audio/*"}),
            "pdf": forms.FileInput(attrs={"accept": ".pdf"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        fields_to_check = ["video", "audio", "pdf", "url", "text_block"]
        for field in fields_to_check:
            value = cleaned_data.get(field)
            if field in ["video", "audio", "pdf"] and value:
                pass  # File sample provided
            elif field in ["url", "text_block"] and value and value.strip():
                pass  # Text/URL sample provided
        return cleaned_data


class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = [
            "available_for_work",
            "hours_per_week",
            "preferred_contract_type",
            "notice_period",
        ]


class ProfileSkillForm(forms.ModelForm):
    skill = forms.ModelChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = ProfileSkill
        fields = ["skill", "proficiency", "years_of_experience"]


class IdentityVerificationForm(forms.ModelForm):
    class Meta:
        model = IdentityVerification
        fields = ["id_card", "proof_of_residence"]
        widgets = {
            "id_card": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}
            ),
            "proof_of_residence": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ["id_card", "proof_of_residence"]:
            document = cleaned_data.get(field_name)
            if document:
                if document.size > 5 * 1024 * 1024:  # 5MB limit
                    self.add_error(field_name, "File size must be under 5MB")
                ext = document.name.split(".")[-1].lower()
                mime_type, _ = mimetypes.guess_type(document.name)
                allowed_mimes = ["application/pdf", "image/jpeg", "image/png"]
                allowed_exts = ["pdf", "jpg", "jpeg", "png"]
                if ext not in allowed_exts or mime_type not in allowed_mimes:
                    self.add_error(
                        field_name, "Only PDF, JPG, JPEG, and PNG files are allowed"
                    )
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        for field_name in ["id_card", "proof_of_residence"]:
            if self.cleaned_data.get(field_name):
                setattr(instance, f"{field_name}_verified", False)
                setattr(instance, f"{field_name}_verified_at", None)
                setattr(instance, f"{field_name}_verified_by", None)
                setattr(instance, f"{field_name}_rejection_reason", None)
        if commit:
            instance.save()
        return instance


# New forms for the vehicle dashboard workflow
class VehicleOwnershipForm(forms.ModelForm):
    """Form for adding vehicles in the new dashboard workflow"""

    plate_number = forms.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r"^[A-Z]SD\s\d{3}\s[A-Z]{2}$",
                message="License plate must follow Eswatini format (e.g., JSD 123 AM)",
            )
        ],
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "JSD 123 AM"}
        ),
    )

    # Add checkbox for owner as operator choice
    will_be_operator = forms.BooleanField(
        required=False,
        initial=False,
        label="I will be the operator of this vehicle",
        help_text="Check this if you will personally drive/operate this vehicle. If unchecked, you can assign operators later.",
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "id": "willBeOperator"}
        ),
    )

    class Meta:
        model = VehicleOwnership
        fields = [
            "plate_number",
            "make",
            "model",
            "year",
            "vehicle_type",
            "will_be_operator",
        ]
        widgets = {
            "make": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., Toyota"}
            ),
            "model": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., Camry"}
            ),
            "year": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1900",
                    "max": str(date.today().year + 1),
                }
            ),
            "vehicle_type": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field not in ["vehicle_type", "will_be_operator"]:
                self.fields[field].widget.attrs.update({"class": "form-control"})

    def clean_year(self):
        year = self.cleaned_data.get("year")
        if year:
            current_year = date.today().year
            if year < 1900:
                raise forms.ValidationError("Year must be 1900 or later.")
            if year > current_year + 1:
                raise forms.ValidationError("Year cannot be in the future.")
        return year


class DocumentForm(forms.ModelForm):
    """Form for uploading documents in the new workflow"""

    class Meta:
        model = Document
        fields = ["doc_type", "file"]
        widgets = {
            "doc_type": forms.Select(attrs={"class": "form-select"}),
            "file": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}
            ),
        }

    def __init__(self, *args, vehicle=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vehicle = vehicle

        # Filter document types based on whether it's vehicle-specific
        if vehicle:
            # Vehicle-specific document types
            self.fields["doc_type"].choices = [
                choice
                for choice in Document.DOC_TYPE_CHOICES
                if choice[0] in ["ROADWORTHY", "BLUEBOOK"]
            ]
        else:
            # User-only document types
            self.fields["doc_type"].choices = [
                choice
                for choice in Document.DOC_TYPE_CHOICES
                if choice[0] in ["DRIVER_LICENSE", "PERMIT"]
            ]

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file:
            # Check file size (5MB limit)
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 5MB")

            # Check file extension and mime type
            ext = file.name.split(".")[-1].lower()
            mime_type, _ = mimetypes.guess_type(file.name)
            allowed_mimes = ["application/pdf", "image/jpeg", "image/png"]
            allowed_exts = ["pdf", "jpg", "jpeg", "png"]

            if ext not in allowed_exts or mime_type not in allowed_mimes:
                raise forms.ValidationError(
                    "Only PDF, JPG, JPEG, and PNG files are allowed"
                )
        return file

    def save(self, user, vehicle=None, commit=True):
        """Save document and create review record"""
        instance = super().save(commit=False)
        instance.user = user
        instance.vehicle = vehicle

        if commit:
            instance.save()
            # Create review record
            DocumentReview.objects.get_or_create(
                document=instance, defaults={"status": "PENDING"}
            )
        return instance


class DocumentReviewForm(forms.ModelForm):
    """Form for admin document review"""

    class Meta:
        model = DocumentReview
        fields = ["status", "reason"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "reason": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Required when rejecting a document...",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        reason = cleaned_data.get("reason")

        # Require reason when rejecting
        if status == "REJECTED" and not reason:
            self.add_error("reason", "Reason is required when rejecting a document.")

        return cleaned_data

    def save(self, reviewed_by, commit=True):
        """Save review with reviewer information"""
        instance = super().save(commit=False)
        instance.reviewed_by = reviewed_by

        if commit:
            instance.save()
        return instance


class FacePhotoForm(forms.Form):
    face_photo_data = forms.CharField(widget=forms.HiddenInput())

    def clean_face_photo_data(self):
        data = self.cleaned_data.get("face_photo_data")
        if not data:
            raise forms.ValidationError("No photo captured.")
        try:
            format_type, img_str = data.split(";base64,")
            ext = format_type.split("/")[-1]  # e.g., 'jpeg'
            if ext not in ["jpg", "jpeg", "png"]:
                raise forms.ValidationError("Only JPG or PNG images are allowed.")
            decoded = base64.b64decode(img_str)
            if len(decoded) > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError("File size must be under 5MB.")
            return {"data": decoded, "ext": ext}
        except Exception:
            raise forms.ValidationError("Invalid image data.")

    def save(self, identity_verification, commit=True):
        cleaned_data = self.cleaned_data.get("face_photo_data")
        if cleaned_data:
            identity_verification.face_photo = ContentFile(
                cleaned_data["data"], name=f"face_photo.{cleaned_data['ext']}"
            )
            identity_verification.face_photo_verified = False
            identity_verification.face_photo_verified_at = None
            identity_verification.face_photo_verified_by = None
            identity_verification.face_photo_rejection_reason = None
            if commit:
                identity_verification.save()
        return identity_verification


class VehicleForm(forms.ModelForm):
    license_plate = forms.CharField(
        max_length=10,
        validators=[
            RegexValidator(
                regex=r"^[A-Z]SD\s\d{3}\s[A-Z][A-Z]$",
                message="License plate must follow Eswatini format (e.g., JSD 123 AM)",
            )
        ],
    )
    year = forms.IntegerField(
        validators=[
            MinValueValidator(1900, message="Year must be 1900 or later"),
            MaxValueValidator(
                date.today().year + 1, message="Year cannot be in the future"
            ),
        ]
    )
    operator_username = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.HiddenInput(attrs={"id": "operator_username"}),
    )

    class Meta:
        model = Vehicle
        fields = [
            "vehicle_type",
            "make",
            "model",
            "year",
            "license_plate",
            "last_inspection_date",
            "next_inspection_date",
            "operator_username",
        ]
        widgets = {
            "last_inspection_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "next_inspection_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "vehicle_type": forms.Select(attrs={"class": "form-select"}),
            "make": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., Toyota"}
            ),
            "model": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., Camry"}
            ),
            "license_plate": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        last_inspection = cleaned_data.get("last_inspection_date")
        next_inspection = cleaned_data.get("next_inspection_date")
        operator_username = cleaned_data.get("operator_username")

        # Validate date range
        if last_inspection and next_inspection:
            if last_inspection > date.today():
                self.add_error(
                    "last_inspection_date",
                    "Last inspection date cannot be in the future",
                )
            if next_inspection <= last_inspection:
                self.add_error(
                    "next_inspection_date",
                    "Next inspection date must be after the last inspection date",
                )
            if next_inspection <= date.today():
                self.add_error(
                    "next_inspection_date", "Next inspection date must be in the future"
                )

        # Validate operator_username
        if operator_username:
            try:
                operator = User.objects.get(username=operator_username)
                if self.request and operator == self.request.user:
                    self.add_error(
                        "operator_username", "You cannot add yourself as an operator."
                    )
                if not operator.profile.is_identity_verified:
                    self.add_error(
                        "operator_username", "Operator must have a verified identity."
                    )
            except User.DoesNotExist:
                self.add_error("operator_username", "User not found.")

        return cleaned_data


class VehicleDocumentForm(forms.ModelForm):
    class Meta:
        model = VehicleDocument
        fields = ["drivers_license", "blue_book", "inspection_certificate", "insurance"]
        widgets = {
            "drivers_license": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}
            ),
            "blue_book": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}
            ),
            "inspection_certificate": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}
            ),
            "insurance": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}
            ),
        }

    def __init__(self, *args, exclude=None, **kwargs):
        super().__init__(*args, **kwargs)
        if exclude:
            for field in exclude:
                if field in self.fields:
                    del self.fields[field]
        self.fields["blue_book"].required = True
        self.fields["inspection_certificate"].required = True
        self.fields["insurance"].required = False
        if "drivers_license" in self.fields:
            self.fields["drivers_license"].required = False

    def clean(self):
        cleaned_data = super().clean()
        for field_name in [
            "drivers_license",
            "blue_book",
            "inspection_certificate",
            "insurance",
        ]:
            if field_name in cleaned_data:
                document = cleaned_data.get(field_name)
                if document:
                    if document.size > 5 * 1024 * 1024:  # 5MB limit
                        self.add_error(field_name, "File size must be under 5MB")
                    ext = document.name.split(".")[-1].lower()
                    mime_type, _ = mimetypes.guess_type(document.name)
                    allowed_mimes = ["application/pdf", "image/jpeg", "image/png"]
                    allowed_exts = ["pdf", "jpg", "jpeg", "png"]
                    if ext not in allowed_exts or mime_type not in allowed_mimes:
                        self.add_error(
                            field_name, "Only PDF, JPG, JPEG, and PNG files are allowed"
                        )
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        for field_name in [
            "drivers_license",
            "blue_book",
            "inspection_certificate",
            "insurance",
        ]:
            if field_name in self.fields and self.cleaned_data.get(field_name):
                setattr(instance, f"{field_name}_verified", False)
                setattr(instance, f"{field_name}_verified_at", None)
                setattr(instance, f"{field_name}_verified_by", None)
                setattr(instance, f"{field_name}_rejection_reason", None)
        if commit:
            instance.save()
        return instance


class GovernmentPermitForm(forms.ModelForm):
    # Mapping from human-readable labels to machine values
    PERMIT_TYPE_MAPPING = {
        "Government Permit": "TRANSPORT",
        "Taxi PSV Permit": "TAXI",
        "Delivery PSV Permit": "DELIVERY",
    }

    # Override permit_type to use custom choices that allow both labels and values
    permit_type = forms.ChoiceField(
        choices=[
            ("TRANSPORT", "Government Permit"),
            ("Government Permit", "Government Permit"),  # Allow human label too
            ("TAXI", "Taxi PSV Permit"),
            ("Taxi PSV Permit", "Taxi PSV Permit"),  # Allow human label too
            ("DELIVERY", "Delivery PSV Permit"),
            ("Delivery PSV Permit", "Delivery PSV Permit"),  # Allow human label too
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    permit_number = forms.CharField(
        max_length=50,
        validators=[
            RegexValidator(
                regex=r"^[A-Z0-9-]+$",
                message="Permit number can only contain uppercase letters, numbers, and hyphens",
            )
        ],
    )

    class Meta:
        model = GovernmentPermit
        fields = [
            "permit_type",
            "permit_number",
            "issue_date",
            "expiry_date",
            "permit_document",
        ]
        widgets = {
            "permit_number": forms.TextInput(attrs={"class": "form-control"}),
            "issue_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "expiry_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "permit_document": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["permit_document"].required = False

    def clean_permit_type(self):
        """Map human-readable permit type labels to machine values"""
        permit_type = self.cleaned_data.get("permit_type")

        # Try to map from human label to machine value
        if permit_type in self.PERMIT_TYPE_MAPPING:
            return self.PERMIT_TYPE_MAPPING[permit_type]

        # If it's already a machine value, keep it
        valid_machine_values = [
            choice[0]
            for choice in GovernmentPermit._meta.get_field("permit_type").choices
        ]
        if permit_type in valid_machine_values:
            return permit_type

        # Default fallback - shouldn't reach here due to choice field validation
        return permit_type

    def clean(self):
        cleaned_data = super().clean()
        issue_date = cleaned_data.get("issue_date")
        expiry_date = cleaned_data.get("expiry_date")
        permit_document = cleaned_data.get("permit_document")

        # Validate date range
        if issue_date and expiry_date:
            if issue_date > date.today():
                self.add_error("issue_date", "Issue date cannot be in the future")
            if expiry_date <= issue_date:
                self.add_error(
                    "expiry_date", "Expiry date must be after the issue date"
                )

        # Validate permit document
        if permit_document:
            if permit_document.size > 5 * 1024 * 1024:  # 5MB limit (increased from 2MB)
                self.add_error("permit_document", "File size must be under 5MB")
            ext = permit_document.name.split(".")[-1].lower()
            mime_type, _ = mimetypes.guess_type(permit_document.name)
            allowed_mimes = ["application/pdf", "image/jpeg", "image/png"]
            allowed_exts = ["pdf", "jpg", "jpeg", "png"]
            if ext not in allowed_exts or mime_type not in allowed_mimes:
                self.add_error(
                    "permit_document", "Only PDF, JPG, JPEG, and PNG files are allowed"
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get("permit_document"):
            instance.is_verified = False
            instance.verified_at = None
            instance.verified_by = None
            instance.rejection_reason = None
        if commit:
            instance.save()
        return instance


class OperatorDocumentForm(forms.ModelForm):
    class Meta:
        model = OperatorDocument
        fields = ["drivers_license"]
        widgets = {
            "drivers_license": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["drivers_license"].required = True

    def clean(self):
        cleaned_data = super().clean()
        drivers_license = cleaned_data.get("drivers_license")
        if drivers_license:
            if drivers_license.size > 2 * 1024 * 1024:  # 2MB limit
                self.add_error("drivers_license", "File size must be under 2MB")
            ext = drivers_license.name.split(".")[-1].lower()
            mime_type, _ = mimetypes.guess_type(drivers_license.name)
            allowed_mimes = ["application/pdf", "image/jpeg", "image/png"]
            allowed_exts = ["pdf", "jpg", "jpeg", "png"]
            if ext not in allowed_exts or mime_type not in allowed_mimes:
                self.add_error(
                    "drivers_license", "Only PDF, JPG, JPEG, and PNG files are allowed"
                )
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get("drivers_license"):
            instance.drivers_license_verified = False
            instance.drivers_license_verified_at = None
            instance.drivers_license_verified_by = None
            instance.drivers_license_rejection_reason = None
        if commit:
            instance.save()
        return instance


class OperatorAssignmentForm(forms.ModelForm):
    """Form for assigning operators to vehicles"""

    operator_identifier = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter username or email",
                "autocomplete": "off",
            }
        ),
        label="Operator Username or Email",
        help_text="Enter the username or email address of the operator you want to assign",
    )

    class Meta:
        model = OperatorAssignment
        fields = []

    def __init__(self, *args, vehicle=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vehicle = vehicle
        if not vehicle:
            raise ValueError("Vehicle is required for operator assignment")

    def clean_operator_identifier(self):
        """Validate and resolve operator identifier to a User instance"""
        identifier = self.cleaned_data.get("operator_identifier")
        if not identifier:
            raise forms.ValidationError("Please provide a username or email address")

        # Try to find user by username first, then by email
        operator = None
        try:
            operator = User.objects.get(username=identifier)
        except User.DoesNotExist:
            try:
                operator = User.objects.get(email=identifier)
            except User.DoesNotExist:
                raise forms.ValidationError(
                    f"No user found with username or email '{identifier}'"
                )

        # Check if user has a profile
        if not hasattr(operator, "profile"):
            raise forms.ValidationError("Selected user does not have a profile")

        # Check if operator is active
        if not operator.is_active:
            raise forms.ValidationError("Selected user account is inactive")

        # Check if operator has identity verification
        if not operator.profile.is_identity_verified:
            raise forms.ValidationError(
                "Operator must have verified identity to be assigned to a vehicle"
            )

        # Check if operator already has an active assignment to this vehicle
        if OperatorAssignment.objects.filter(
            vehicle=self.vehicle, operator=operator, active=True
        ).exists():
            raise forms.ValidationError(
                "This operator is already assigned to this vehicle"
            )

        # Check if operator has an active assignment to another vehicle
        active_assignment = (
            OperatorAssignment.objects.filter(operator=operator, active=True)
            .exclude(vehicle=self.vehicle)
            .first()
        )

        if active_assignment:
            raise forms.ValidationError(
                f"This operator is already assigned to vehicle {active_assignment.vehicle.plate_number}. "
                "Each operator can only be assigned to one vehicle at a time."
            )

        # Store the resolved operator for use in save method
        self.resolved_operator = operator
        return identifier

    def save(self, assigned_by, commit=True):
        """Create the operator assignment"""
        if not hasattr(self, "resolved_operator"):
            raise ValueError("Form must be validated before saving")

        # Deactivate any existing assignments for this vehicle
        OperatorAssignment.objects.filter(vehicle=self.vehicle, active=True).update(
            active=False, deactivated_at=timezone.now()
        )

        # Create new assignment
        assignment = OperatorAssignment.objects.create(
            vehicle=self.vehicle,
            operator=self.resolved_operator,
            assigned_by=assigned_by,
        )

        return assignment
