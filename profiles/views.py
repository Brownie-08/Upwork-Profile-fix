from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User


def is_ajax(request):
    """Check if request is an AJAX request"""
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


import logging
from django.contrib.auth.models import User
from django.db.models import Q
import base64
from PIL import Image
from django.core.files.base import ContentFile
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from decimal import Decimal
import io
from django.utils import timezone
from .services.otp import OTPService
from .services.notify import notify_admins
from .csrf_debug import csrf_debug_view, csrf_test_endpoint

from .models import (
    Profile,
    Experience,
    Education,
    Portfolio,
    ProfileSkill,
    Skill,
    PortfolioSample,
    Availability,
    Vehicle,
    IdentityVerification,
    VehicleDocument,
    GovernmentPermit,
    OperatorDocument,
    OperatorAssignment,
    TransportOwnerBadge,
    Document,
    DocumentReview,
    VehicleOwnership,
)
from .forms import (
    UserRegisterForm,
    ExperienceForm,
    EducationForm,
    VehicleForm,
    PortfolioForm,
    PortfolioSampleForm,
    AvailabilityForm,
    IdentityVerificationForm,
    VehicleDocumentForm,
    GovernmentPermitForm,
    FacePhotoForm,
    OperatorDocumentForm,
    OperatorAssignmentForm,
)

# Set up logging
logger = logging.getLogger(__name__)


def register(request):
    """Handle user registration with OTP verification."""
    if request.method == "POST":
        # Log CSRF debug information for troubleshooting
        logger.info(f"Registration POST attempt from {request.get_host()}")
        logger.info(f"CSRF Token in POST: {request.POST.get('csrfmiddlewaretoken', 'NOT FOUND')[:10]}...")
        logger.info(f"Request secure: {request.is_secure()}")
        
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Deactivate until OTP verification
            user.save()

            # Create or get profile
            profile, created = Profile.objects.get_or_create(user=user)

            # Set phone number from form if provided
            phone_number = form.cleaned_data.get("phone_number")
            if phone_number:
                profile.phone_number = phone_number
                profile.save()

            # Handle referral code
            referral_code = form.cleaned_data.get("referral_code")
            if referral_code:
                from .services.referral import ReferralService

                success, message, referrer = ReferralService.assign_referrer(
                    user, referral_code
                )
                if success and referrer:
                    messages.success(
                        request,
                        f"You were referred by {referrer.get_full_name() or referrer.username}!",
                    )
                    logger.info(f"User {user.username} referred by {referrer.username}")
                elif not success:
                    messages.warning(request, message)
                    logger.warning(f"Referral failed for {user.username}: {message}")

            # Create referral record for new user (auto-generates code)
            from .services.referral import ReferralService

            ReferralService.create_referral(user)

            # Create OTP for account verification (email + SMS if available)
            channel = "BOTH" if profile.phone_number else "EMAIL"
            otp = OTPService.create_otp(user, "VERIFY", channel)

            if otp:
                # Store user ID in session for verification process
                request.session["otp_user_id"] = user.id
                messages.success(
                    request,
                    "Account created successfully! Please check your email for a verification code.",
                )
                logger.info(
                    f"User {user.username} registered, OTP {otp.code} sent to {user.email}"
                )
                return redirect("profiles:verify_account")
            else:
                messages.error(
                    request, "Error sending verification code. Please try again later."
                )
                logger.error(
                    f"Failed to create OTP for {user.email} during registration"
                )
                user.delete()
                return redirect("profiles:register")
        else:
            messages.error(request, "Please correct the errors below.")
            logger.warning(f"Registration failed for form data: {form.errors}")
    else:
        form = UserRegisterForm()
    return render(request, "profiles/register.html", {"form": form})


def confirm_email(request, uidb64, token):
    """Handle email confirmation via one-time link."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
        logger.warning(
            f"Invalid email confirmation attempt: uid={uidb64}, token={token}"
        )

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Your email has been confirmed! You can now log in.")
        logger.info(f"Email confirmed for user {user.username}")
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("profiles:profile")
    else:
        messages.error(request, "The confirmation link is invalid or has expired.")
        logger.warning(f"Failed email confirmation for uid={uidb64}, token={token}")
        return redirect("login")


@login_required
def profile(request):
    """Display user profile with related information."""
    profile, created = Profile.objects.get_or_create(user=request.user)

    experiences = Experience.objects.filter(profile=profile).order_by("-start_date")
    education = Education.objects.filter(profile=profile).order_by("-start_date")
    portfolio_samples = Portfolio.objects.filter(user=request.user).order_by(
        "-completion_date"
    )
    availability = Availability.objects.filter(profile=profile).first()
    vehicles = Vehicle.objects.filter(profile=profile)
    operated_vehicles = Vehicle.objects.filter(operators=request.user)
    permits = GovernmentPermit.objects.filter(profile=profile)
    profile_skills = ProfileSkill.objects.filter(profile=profile).select_related(
        "skill"
    )
    # Get operator documents for:
    # 1. Current user as operator
    # 2. Operators assigned to current user's vehicles
    operator_documents = OperatorDocument.objects.filter(
        Q(user=request.user) |
        Q(vehicle__profile=profile)
    ).distinct().select_related('user', 'vehicle')

    # Fetch identity document statuses from DocumentReview system
    identity_documents = []
    identity_doc_types = [
        ("id_card", "Government ID", "id-card", "ID_CARD"),
        ("face_photo", "Face Photo", "user", "FACE_PHOTO"),
        ("proof_of_residence", "Proof of Residence", "home", "PROOF_OF_RESIDENCE"),
    ]

    identity_doc_statuses = {}
    for field, label, icon, doc_type in identity_doc_types:
        try:
            # Identity documents have vehicle=None - use filter and first() to handle duplicates
            documents = Document.objects.filter(
                user=request.user, doc_type=doc_type, vehicle__isnull=True
            )
            if documents.exists():
                document = (
                    documents.first()
                )  # Get the first document if duplicates exist
                if hasattr(document, "review"):
                    status = document.review.status
                    reason = (
                        document.review.reason
                        if document.review.status == "REJECTED"
                        else None
                    )
                else:
                    status = "PENDING"
                    reason = None
                logger.debug(
                    f"Found {doc_type} document for {request.user.username}: status={status}"
                )

                # Clean up duplicate documents if any exist
                if documents.count() > 1:
                    logger.warning(
                        f"Found {documents.count()} duplicate {doc_type} documents for {request.user.username}, cleaning up..."
                    )
                    # Keep the first document, delete the rest
                    duplicate_ids = list(
                        documents.values_list("id", flat=True)[1:]
                    )  # Skip first
                    Document.objects.filter(id__in=duplicate_ids).delete()
                    logger.info(
                        f"Cleaned up {len(duplicate_ids)} duplicate {doc_type} documents for {request.user.username}"
                    )
            else:
                status = "MISSING"
                reason = None
                logger.debug(
                    f"No {doc_type} document found for {request.user.username}"
                )
        except Exception as e:
            status = "MISSING"
            reason = None
            logger.error(
                f"Error fetching {doc_type} document for {request.user.username}: {str(e)}"
            )

        identity_doc_statuses[field] = {
            "status": status,
            "reason": reason,
            "label": label,
            "icon": icon,
        }
        identity_documents.append((field, label, icon, status, reason))

    vehicle_document_fields = [
        ("drivers_license", "Driver’s License"),
        ("blue_book", "Registration Certificate (Blue Book)"),
        ("inspection_certificate", "Roadworthiness Certificate"),
        ("insurance", "Insurance"),
    ]

    # Get referral statistics
    from .services.referral import ReferralService

    referral_stats = ReferralService.get_referral_stats(request.user)

    # Get transport owner badge status
    transport_badge = None
    try:
        transport_badge = TransportOwnerBadge.objects.get(user=request.user)
    except TransportOwnerBadge.DoesNotExist:
        pass

    context = {
        "user": request.user,
        "profile": profile,
        "vehicles": vehicles,
        "operated_vehicles": operated_vehicles,
        "permits": permits,
        "experiences": experiences,
        "portfolio": portfolio_samples,
        "education": education,
        "profile_skills": profile_skills,
        "availability": availability,
        "identity_documents": identity_documents,
        "vehicle_document_fields": vehicle_document_fields,
        "operator_documents": operator_documents,
        "referral_stats": referral_stats,
        "transport_badge": transport_badge,
    }

    logger.debug(
        f"Rendering profile for user: {request.user.username}, is_identity_verified: {profile.is_identity_verified}, is_vehicle_verified: {profile.is_vehicle_verified}, is_permit_verified: {profile.is_permit_verified}"
    )
    return render(request, "profiles/profile.html", context)


@login_required
def add_vehicle(request):
    """Add a new vehicle with inline document upload and optional operator selection."""
    profile = request.user.profile
    vehicle_document_fields = [
        ("drivers_license", "Driver’s License"),
        ("blue_book", "Registration Certificate (Blue Book)"),
        ("inspection_certificate", "Roadworthiness Certificate"),
        ("insurance", "Insurance"),
    ]
    if request.method == "POST":
        logger.debug(f"POST data: {request.POST}, FILES: {request.FILES}")
        if not profile.is_identity_verified:
            logger.warning(
                f"User {request.user.username} attempted to add vehicle without identity verification"
            )
            return JsonResponse(
                {
                    "success": False,
                    "errors": [
                        {"field": None, "message": "Identity verification required"}
                    ],
                },
                status=403,
            )

        form = VehicleForm(request.POST, request.FILES)
        is_owner_operator = request.POST.get("is_owner_operator") == "on"
        doc_form = (
            VehicleDocumentForm(request.POST, request.FILES)
            if is_owner_operator
            else VehicleDocumentForm(
                request.POST, request.FILES, exclude=["drivers_license"]
            )
        )
        operator_username = (
            request.POST.get("operator_username") if not is_owner_operator else None
        )

        if form.is_valid() and doc_form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.profile = profile
            vehicle.is_verified = False
            vehicle.save()

            document = doc_form.save(commit=False)
            document.vehicle = vehicle
            if is_owner_operator:
                document.drivers_license_verified = False
            else:
                document.drivers_license = None
                document.drivers_license_verified = (
                    True  # No driver’s license required for non-owner operator
                )
            document.save()

            if is_owner_operator:
                OperatorDocument.objects.create(
                    user=request.user,
                    vehicle=vehicle,
                    drivers_license=document.drivers_license,
                    drivers_license_verified=False,
                )
                vehicle.operators.add(request.user)
                logger.info(
                    f"Owner {request.user.username} added as operator for vehicle {vehicle.license_plate}"
                )
            elif operator_username:
                try:
                    operator = User.objects.get(username=operator_username)
                    if operator == request.user:
                        vehicle.delete()
                        document.delete()
                        return JsonResponse(
                            {
                                "success": False,
                                "errors": [
                                    {
                                        "field": "operator_username",
                                        "message": "Cannot add yourself as an operator",
                                    }
                                ],
                            },
                            status=400,
                        )
                    if not operator.profile.is_identity_verified:
                        vehicle.delete()
                        document.delete()
                        return JsonResponse(
                            {
                                "success": False,
                                "errors": [
                                    {
                                        "field": "operator_username",
                                        "message": "Operator must have verified identity",
                                    }
                                ],
                            },
                            status=400,
                        )
                    vehicle.operators.add(operator)
                    logger.info(
                        f"Operator {operator.username} added to vehicle {vehicle.license_plate} by {request.user.username}"
                    )
                except User.DoesNotExist:
                    vehicle.delete()
                    document.delete()
                    logger.warning(
                        f"Attempt to add non-existent operator {operator_username} by {request.user.username}"
                    )
                    return JsonResponse(
                        {
                            "success": False,
                            "errors": [
                                {
                                    "field": "operator_username",
                                    "message": "User not found",
                                }
                            ],
                        },
                        status=400,
                    )

            logger.info(
                f"Vehicle {vehicle.license_plate} and documents added by {request.user.username}"
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": "Vehicle and documents added successfully. Awaiting verification.",
                    "vehicle_id": vehicle.id,
                    "redirect_url": reverse("profiles:profile"),
                }
            )
        else:
            errors = [
                {"field": field, "message": msg}
                for field, errors in (form.errors.items() | doc_form.errors.items())
                for msg in errors
            ]
            logger.warning(
                f"Vehicle form validation failed for {request.user.username}: {errors}"
            )
            return JsonResponse({"success": False, "errors": errors}, status=400)
    else:
        form = VehicleForm()
        doc_form = VehicleDocumentForm()
        logger.debug(
            f"Rendering add_vehicle.html with vehicle_document_fields: {vehicle_document_fields}"
        )
    return render(
        request,
        "profiles/add_vehicle.html",
        {
            "form": form,
            "doc_form": doc_form,
            "vehicle_document_fields": vehicle_document_fields,
        },
    )


@login_required
def edit_vehicle(request, vehicle_id):
    """Edit an existing vehicle, including operator management."""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id, profile=request.user.profile)
    vehicle_document_fields = [
        ("drivers_license", "Driver’s License"),
        ("blue_book", "Registration Certificate (Blue Book)"),
        ("inspection_certificate", "Roadworthiness Certificate"),
        ("insurance", "Insurance"),
    ]
    document = vehicle.documents.first()
    is_owner_operator = OperatorDocument.objects.filter(
        user=request.user, vehicle=vehicle
    ).exists()

    if request.method == "POST":
        logger.debug(
            f"POST data for edit_vehicle: {request.POST}, FILES: {request.FILES}"
        )
        form = VehicleForm(request.POST, request.FILES, instance=vehicle)
        is_owner_operator_new = request.POST.get("is_owner_operator") == "on"
        doc_form = (
            VehicleDocumentForm(request.POST, request.FILES, instance=document)
            if is_owner_operator_new
            else VehicleDocumentForm(
                request.POST,
                request.FILES,
                instance=document,
                exclude=["drivers_license"],
            )
        )
        operator_username = (
            request.POST.get("operator_username") if not is_owner_operator_new else None
        )

        if form.is_valid() and doc_form.is_valid():
            vehicle = form.save()
            document = doc_form.save(commit=False)
            document.vehicle = vehicle
            if is_owner_operator_new:
                document.drivers_license_verified = False
            else:
                document.drivers_license = None
                document.drivers_license_verified = True
            document.save()

            if is_owner_operator_new and not is_owner_operator:
                OperatorDocument.objects.create(
                    user=request.user,
                    vehicle=vehicle,
                    drivers_license=document.drivers_license,
                    drivers_license_verified=False,
                )
                vehicle.operators.add(request.user)
                logger.info(
                    f"Owner {request.user.username} added as operator for vehicle {vehicle.license_plate}"
                )
            elif not is_owner_operator_new and is_owner_operator:
                vehicle.operators.remove(request.user)
                OperatorDocument.objects.filter(
                    user=request.user, vehicle=vehicle
                ).delete()
                logger.info(
                    f"Owner {request.user.username} removed as operator for vehicle {vehicle.license_plate}"
                )

            if operator_username:
                try:
                    operator = User.objects.get(username=operator_username)
                    if operator == request.user:
                        return JsonResponse(
                            {
                                "success": False,
                                "errors": [
                                    {
                                        "field": "operator_username",
                                        "message": "Cannot add yourself as an operator",
                                    }
                                ],
                            },
                            status=400,
                        )
                    if not operator.profile.is_identity_verified:
                        return JsonResponse(
                            {
                                "success": False,
                                "errors": [
                                    {
                                        "field": "operator_username",
                                        "message": "Operator must have verified identity",
                                    }
                                ],
                            },
                            status=400,
                        )
                    if operator not in vehicle.operators.all():
                        vehicle.operators.add(operator)
                        logger.info(
                            f"Operator {operator.username} added to vehicle {vehicle.license_plate} by {request.user.username}"
                        )
                except User.DoesNotExist:
                    logger.warning(
                        f"Attempt to add non-existent operator {operator_username} by {request.user.username}"
                    )
                    return JsonResponse(
                        {
                            "success": False,
                            "errors": [
                                {
                                    "field": "operator_username",
                                    "message": "User not found",
                                }
                            ],
                        },
                        status=400,
                    )

            logger.info(
                f"Vehicle {vehicle.license_plate} updated by {request.user.username}"
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": "Vehicle updated successfully. Awaiting verification.",
                    "redirect_url": reverse("profiles:profile"),
                }
            )
        else:
            errors = [
                {"field": field, "message": msg}
                for field, errors in (form.errors.items() | doc_form.errors.items())
                for msg in errors
            ]
            logger.warning(f"Vehicle edit failed for {request.user.username}: {errors}")
            return JsonResponse({"success": False, "errors": errors}, status=400)
    else:
        form = VehicleForm(instance=vehicle)
        doc_form = VehicleDocumentForm(instance=document)
        logger.debug(f"Rendering edit_vehicle.html for vehicle {vehicle_id}")
    return render(
        request,
        "profiles/edit_vehicle.html",
        {
            "form": form,
            "doc_form": doc_form,
            "vehicle": vehicle,
            "vehicle_document_fields": vehicle_document_fields,
            "is_owner_operator": is_owner_operator,
        },
    )


@login_required
def upload_operator_document(request, vehicle_id):
    """Allow operator to upload their driver's license for a specific vehicle."""
    # Check if user is vehicle owner or assigned operator
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
        is_owner = hasattr(vehicle, "profile") and vehicle.profile.user == request.user
        is_assigned_operator = vehicle.operators.filter(id=request.user.id).exists()

        if not (is_owner or is_assigned_operator):
            logger.warning(
                f"User {request.user.username} attempted to upload operator document for vehicle {vehicle_id} without permission"
            )
            return JsonResponse(
                {
                    "success": False,
                    "errors": [
                        {
                            "field": None,
                            "message": "You must be the vehicle owner or an assigned operator to upload documents",
                        }
                    ],
                },
                status=403,
            )
    except Vehicle.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "errors": [{"field": None, "message": "Vehicle not found"}],
            },
            status=404,
        )

    # Log warning if vehicle is not verified for audit purposes
    if not vehicle.is_verified:
        logger.info(
            f"Operator document uploaded for unverified vehicle {vehicle.id} by {request.user.username} - flagged for review"
        )

    if request.method == "POST":
        existing_doc = OperatorDocument.objects.filter(
            user=request.user, vehicle=vehicle
        ).first()
        doc_form = OperatorDocumentForm(
            request.POST, request.FILES, instance=existing_doc
        )
        if doc_form.is_valid():
            operator_doc = doc_form.save(commit=False)
            operator_doc.user = request.user
            operator_doc.vehicle = vehicle
            operator_doc.drivers_license_verified = False
            operator_doc.save()
            logger.info(
                f"Driver’s license uploaded by {request.user.username} for vehicle {vehicle.license_plate}"
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": "Driver’s license uploaded successfully. Awaiting verification.",
                    "redirect_url": reverse("profiles:profile"),
                }
            )
        else:
            logger.warning(
                f"Operator document upload failed for {request.user.username}: {doc_form.errors}"
            )
            errors = [
                {"field": field, "message": msg}
                for field, errors_list in doc_form.errors.items()
                for msg in errors_list
            ]
            return JsonResponse({"success": False, "errors": errors}, status=400)
    else:
        doc_form = OperatorDocumentForm(
            instance=OperatorDocument.objects.filter(
                user=request.user, vehicle=vehicle
            ).first()
        )
    return render(
        request,
        "profiles/upload_operator_document.html",
        {"vehicle": vehicle, "doc_form": doc_form},
    )


@login_required
def add_vehicle_operator(request, vehicle_id):
    """Enhanced operator assignment with identity verification and transport provider status."""
    # Handle both Vehicle and VehicleOwnership models
    # Try both models and use whichever one exists and belongs to the user
    vehicle = None
    vehicle_model = None

    # Try both models simultaneously to avoid ID conflicts between tables
    legacy_vehicle = None
    new_vehicle = None

    try:
        legacy_vehicle = Vehicle.objects.get(id=vehicle_id, profile__user=request.user)
        logger.info(
            f"Found legacy vehicle: {legacy_vehicle.license_plate} (ID={legacy_vehicle.id})"
        )
    except Vehicle.DoesNotExist:
        logger.info(f"No legacy vehicle found with ID={vehicle_id}")
        pass

    try:
        new_vehicle = VehicleOwnership.objects.get(id=vehicle_id, owner=request.user)
        logger.info(
            f"Found new vehicle: {new_vehicle.plate_number} (ID={new_vehicle.id})"
        )
    except VehicleOwnership.DoesNotExist:
        logger.info(f"No new vehicle found with ID={vehicle_id}")
        pass

    # Determine which one to use
    # If both exist (rare), prefer legacy to maintain backwards compatibility
    if legacy_vehicle is not None:
        vehicle = legacy_vehicle
        vehicle_model = "legacy"
        logger.info(
            f"Selected legacy vehicle: {vehicle.license_plate} (ID={vehicle.id})"
        )
    elif new_vehicle is not None:
        vehicle = new_vehicle
        vehicle_model = "new"
        logger.info(f"Selected new vehicle: {vehicle.plate_number} (ID={vehicle.id})")
    else:
        logger.info(
            f"No vehicle found with ID={vehicle_id} for user {request.user.username}"
        )
        messages.error(
            request, "Vehicle not found or you don't have permission to manage it."
        )
        return redirect("profiles:profile")

    if request.method == "POST":
        operator_username = request.POST.get("operator_username", "").strip()

        if not operator_username:
            if is_ajax(request):
                return JsonResponse(
                    {"success": False, "message": "Please select an operator."},
                    status=400,
                )
            messages.error(request, "Please select an operator.")
            return redirect(request.path)

        try:
            operator = User.objects.get(username=operator_username)

            # Validation checks
            if operator == request.user:
                error_msg = "You cannot assign yourself as an operator."
                if is_ajax(request):
                    return JsonResponse(
                        {"success": False, "message": error_msg}, status=400
                    )
                messages.error(request, error_msg)
                return redirect(request.path)

            # Check if operator's identity is verified
            if not operator.profile.is_identity_verified:
                error_msg = f"Cannot assign {operator.get_full_name() or operator.username}. They must verify their identity first (ID card, face photo, and proof of residence)."
                if is_ajax(request):
                    return JsonResponse(
                        {"success": False, "message": error_msg}, status=400
                    )
                messages.error(request, error_msg)
                return redirect(request.path)

            # Check if operator is already assigned to this vehicle
            if vehicle_model == "legacy":
                if operator in vehicle.operators.all():
                    error_msg = f"{operator.get_full_name() or operator.username} is already assigned to this vehicle."
                    if is_ajax(request):
                        return JsonResponse(
                            {"success": False, "message": error_msg}, status=400
                        )
                    messages.warning(request, error_msg)
                    return redirect(request.path)

                # Add operator to legacy vehicle
                vehicle.operators.add(operator)

                # Create OperatorDocument record for display purposes, even for legacy vehicles
                # This ensures the operator documents section shows assigned operators
                operator_doc, created = OperatorDocument.objects.get_or_create(
                    user=operator,
                    vehicle=vehicle,
                    defaults={
                        "drivers_license_verified": False  # Will need to upload license
                    },
                )
                if created:
                    logger.info(
                        f"OperatorDocument created for legacy vehicle: {operator.username} -> {vehicle.license_plate}"
                    )

                # Skip creating OperatorAssignment for legacy vehicles to avoid model mismatch
                # Legacy vehicles use Vehicle model, but OperatorAssignment expects VehicleOwnership
                logger.info(
                    f"Legacy vehicle operator assignment: {operator.username} -> {vehicle.license_plate} (OperatorAssignment record skipped for legacy compatibility)"
                )
            else:
                # Check for existing active assignment
                existing_assignment = OperatorAssignment.objects.filter(
                    vehicle=vehicle, active=True
                ).first()

                if existing_assignment:
                    error_msg = f"Vehicle already has an active operator: {existing_assignment.operator.get_full_name() or existing_assignment.operator.username}"
                    if is_ajax(request):
                        return JsonResponse(
                            {"success": False, "message": error_msg}, status=400
                        )
                    messages.error(request, error_msg)
                    return redirect(request.path)

                # Create new operator assignment
                assignment = OperatorAssignment.objects.create(
                    vehicle=vehicle,
                    operator=operator,
                    assigned_by=request.user,
                    active=True,
                )

            # Update both vehicle owner and operator to TRANSPORT status
            # Vehicle owner becomes transport provider
            if request.user.profile.account_type != "TRANSPORT":
                request.user.profile.account_type = "TRANSPORT"
                request.user.profile.save()
                logger.info(
                    f"Vehicle owner {request.user.username} upgraded to TRANSPORT status"
                )

            # Operator becomes transport provider if identity is verified
            if (
                operator.profile.is_identity_verified
                and operator.profile.account_type != "TRANSPORT"
            ):
                operator.profile.account_type = "TRANSPORT"
                operator.profile.save()
                logger.info(
                    f"Operator {operator.username} upgraded to TRANSPORT status"
                )

            # Send notification to operator
            from notifications.models import Notification

            # Robust vehicle info building
            plate = getattr(
                vehicle, "plate_number", getattr(vehicle, "license_plate", "N/A")
            )
            year = getattr(vehicle, "year", None)
            make = getattr(vehicle, "make", None)
            model = getattr(vehicle, "model", None)
            vehicle_info = f"{year or ''} {make or ''} {model or ''} ({plate})".strip()
            if vehicle_info.startswith("("):
                vehicle_info = f"Vehicle {plate}"

            Notification.objects.create(
                user=operator,
                title="Vehicle Operator Assignment",
                message=f"You have been assigned as an operator for {vehicle_info} by {request.user.get_full_name() or request.user.username}. You now have Transport Service Provider status.",
                notification_type="operator_assigned",
            )

            success_msg = f"{operator.get_full_name() or operator.username} has been successfully assigned as operator. Both you and the operator now have Transport Service Provider status."

            logger.info(
                f"Operator {operator.username} assigned to vehicle {plate} by {request.user.username}"
            )

            if is_ajax(request):
                return JsonResponse(
                    {
                        "success": True,
                        "message": success_msg,
                        "redirect_url": reverse("profiles:profile"),
                    }
                )

            messages.success(request, success_msg)
            return redirect("profiles:profile")

        except User.DoesNotExist:
            error_msg = "Selected user not found. Please try again."
            if is_ajax(request):
                return JsonResponse(
                    {"success": False, "message": error_msg}, status=400
                )
            messages.error(request, error_msg)
            return redirect(request.path)

        except Exception as e:
            logger.exception(f"Error assigning operator: {str(e)}")
            error_msg = (
                "An error occurred while assigning the operator. Please try again."
            )
            if is_ajax(request):
                return JsonResponse(
                    {"success": False, "message": error_msg}, status=500
                )
            messages.error(request, error_msg)
            return redirect(request.path)

    # GET request - render the assignment page
    # Get users with approved identity documents for operator selection (excluding current user)
    from .models import Document, DocumentReview

    # Get users who have all three identity documents approved
    approved_users = []
    all_users = User.objects.exclude(id=request.user.id).select_related("profile")

    for user in all_users:
        try:
            if hasattr(user, "profile") and user.profile.is_identity_verified:
                approved_users.append(user)
        except:
            # Skip users without profiles
            continue

    verified_users = approved_users

    # Check if vehicle already has an operator (for new system)
    existing_assignment = None
    if vehicle_model == "new":
        existing_assignment = OperatorAssignment.objects.filter(
            vehicle=vehicle, active=True
        ).first()

    context = {
        "vehicle": vehicle,
        "verified_users": verified_users,
        "existing_assignment": existing_assignment,
        "vehicle_model": vehicle_model,
    }

    return render(request, "profiles/add_vehicle_operator.html", context)


@login_required
def remove_vehicle_operator(request, vehicle_id, operator_id):
    """Remove a user as an operator of a vehicle with double confirmation."""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id, profile=request.user.profile)
    operator = get_object_or_404(User, id=operator_id)
    if operator == request.user:
        logger.warning(
            f"User {request.user.username} attempted to remove themselves as operator"
        )
        return JsonResponse(
            {
                "success": False,
                "errors": [
                    {
                        "field": None,
                        "message": "Cannot remove yourself as operator via this action",
                    }
                ],
            },
            status=400,
        )

    if request.method == "POST":
        confirmation = request.POST.get("confirmation")
        if confirmation == "confirm":
            vehicle.operators.remove(operator)
            OperatorDocument.objects.filter(user=operator, vehicle=vehicle).delete()
            if (
                not operator.operated_vehicles.filter(
                    is_verified=True, operator_documents__drivers_license_verified=True
                ).exists()
                and not operator.profile.vehicles.filter(is_verified=True).exists()
            ):
                operator.profile.account_type = "REGULAR"
                operator.profile.save()
                logger.info(f"Operator {operator.username} account_type set to REGULAR")
            logger.info(
                f"User {operator.username} removed as operator from vehicle {vehicle.license_plate} by {request.user.username}"
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": f"User {operator.username} removed as operator.",
                    "redirect_url": reverse("profiles:profile"),
                }
            )
        else:
            logger.warning(
                f"Operator removal for {operator.username} by {request.user.username} failed due to missing confirmation"
            )
            return JsonResponse(
                {
                    "success": False,
                    "errors": [{"field": None, "message": "Confirmation required"}],
                },
                status=400,
            )
    return render(
        request,
        "profiles/remove_vehicle_operator.html",
        {"vehicle": vehicle, "operator": operator},
    )


@login_required
def search_users(request):
    """Search users by username, email, first name, or last name for operator selection."""
    query = request.GET.get("q", "")
    if not query or len(query.strip()) < 2:
        return JsonResponse({"users": []})

    # Search by username, email, first name, or last name
    all_matching_users = (
        User.objects.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
        .exclude(id=request.user.id)
        .select_related("profile")[:30]
    )

    # Filter for identity-verified users
    users = []
    for user in all_matching_users:
        try:
            if hasattr(user, "profile") and user.profile.is_identity_verified:
                users.append(user)
        except:
            # Skip users without profiles
            continue
    users = users[:15]

    results = [
        {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_verified": user.profile.is_identity_verified,
        }
        for user in users
    ]

    logger.debug(
        f"User search by {request.user.username} for query '{query}': {len(results)} results"
    )
    return JsonResponse({"users": results})


# Unchanged views below
@login_required
def edit_vehicle_document(request, vehicle_id, document_id):
    """Edit an existing vehicle document."""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id, profile=request.user.profile)
    document = get_object_or_404(VehicleDocument, id=document_id, vehicle=vehicle)
    vehicle_document_fields = [
        ("drivers_license", "Driver’s License"),
        ("blue_book", "Registration Certificate (Blue Book)"),
        ("inspection_certificate", "Roadworthiness Certificate"),
        ("insurance", "Insurance"),
    ]
    if request.method == "POST":
        logger.debug(
            f"POST data for edit_vehicle_document: {request.POST}, FILES: {request.FILES}"
        )
        form = VehicleDocumentForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            form.save()
            logger.info(
                f"Vehicle document {document_id} for vehicle {vehicle.license_plate} updated by {request.user.username}"
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": "Documents updated successfully. Awaiting verification.",
                    "redirect_url": reverse("profiles:profile"),
                }
            )
        else:
            logger.warning(
                f"Vehicle document form validation failed for {request.user.username}: {form.errors}"
            )
            errors = [
                {"field": field, "message": msg}
                for field, errors in form.errors.items()
                for msg in errors
            ]
            return JsonResponse({"success": False, "errors": errors}, status=400)
    else:
        form = VehicleDocumentForm(instance=document)
        logger.debug(
            f"Rendering edit_vehicle_document.html for vehicle {vehicle_id}, document {document_id}"
        )
    return render(
        request,
        "profiles/edit_vehicle_document.html",
        {
            "form": form,
            "vehicle": vehicle,
            "document": document,
            "vehicle_document_fields": vehicle_document_fields,
        },
    )


@login_required
def add_permit(request):
    """Add a new government permit with inline document upload."""
    profile = request.user.profile
    if request.method == "POST":
        if profile.account_type != "TRANSPORT":
            logger.warning(
                f"User {request.user.username} attempted to add permit without TRANSPORT account type"
            )
            return JsonResponse(
                {
                    "success": False,
                    "errors": [
                        {
                            "field": None,
                            "message": "Only Transport Service Providers can add permits",
                        }
                    ],
                },
                status=403,
            )

        form = GovernmentPermitForm(request.POST, request.FILES)
        if form.is_valid():
            permit = form.save(commit=False)
            permit.profile = profile
            # Respect the form-mapped permit_type instead of overriding
            permit.save()
            logger.info(
                f"Permit {permit.permit_number} added by {request.user.username}"
            )

            # Send admin notification
            notify_admins(
                "permit_created",
                f"Permit {permit.permit_number} created by {request.user.username}",
                {"permit_id": permit.id, "user_id": request.user.id},
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": "Permit added successfully.",
                    "permit_id": permit.id,
                    "redirect_url": reverse("profiles:profile"),
                }
            )
        else:
            logger.warning(
                f"Permit form validation failed for {request.user.username}: {form.errors}"
            )
            # Build consistent error format like edit_vehicle_document
            errors = [
                {"field": field, "message": msg}
                for field, errors_list in form.errors.items()
                for msg in errors_list
            ]
            return JsonResponse({"success": False, "errors": errors}, status=400)
    else:
        form = GovernmentPermitForm()
    return render(request, "profiles/add_permit.html", {"form": form})


@login_required
def edit_permit_document(request, permit_id):
    """Edit a government permit document."""
    permit = get_object_or_404(
        GovernmentPermit, id=permit_id, profile=request.user.profile
    )

    if request.method == "POST":
        form = GovernmentPermitForm(request.POST, request.FILES, instance=permit)
        if form.is_valid():
            form.save()
            logger.info(
                f"Permit document updated for {permit.permit_number} by {request.user.username}"
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": "Permit document updated successfully.",
                    "redirect_url": reverse("profiles:profile"),
                }
            )
        else:
            logger.warning(
                f"Permit document edit failed for {request.user.username}: {form.errors}"
            )
            # Build consistent error format like add_permit
            errors = [
                {"field": field, "message": msg}
                for field, errors_list in form.errors.items()
                for msg in errors_list
            ]
            return JsonResponse({"success": False, "errors": errors}, status=400)
    else:
        form = GovernmentPermitForm(instance=permit)

    return render(
        request,
        "profiles/edit_permit_document.html",
        {"form": form, "permit": permit, "label": "Transport Permit"},
    )


@login_required
def upload_identity_document(request, field):
    """Upload an identity document."""
    # Special handling for face_photo GET requests - show webcam capture page
    if request.method == "GET" and field == "face_photo":
        return render(request, "profiles/face_photo_capture.html")
    
    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "errors": [{"field": None, "message": "Only POST method allowed."}],
            },
            status=405,
        )

    valid_fields = ["id_card", "proof_of_residence", "face_photo"]
    if field not in valid_fields:
        return JsonResponse(
            {
                "success": False,
                "errors": [{"field": None, "message": "Invalid document field."}],
            },
            status=400,
        )

    # Map field names to Document doc_type values
    doc_type_mapping = {
        "id_card": "ID_CARD",
        "proof_of_residence": "PROOF_OF_RESIDENCE",
        "face_photo": "FACE_PHOTO",
    }

    try:
        from .models import Document, DocumentReview

        # Handle face_photo from either webcam capture (base64) or file upload
        if field == "face_photo":
            # Check if this is base64 data from webcam
            if "face_photo_data" in request.POST and request.POST.get("face_photo_data"):
                face_photo_data = request.POST.get("face_photo_data")
                if not face_photo_data:
                    if is_ajax(request):
                        return JsonResponse({
                            "success": False,
                            "errors": [{"field": None, "message": "No photo captured. Please capture a photo first."}]
                        }, status=400)
                    else:
                        messages.error(request, "No photo captured. Please capture a photo first.")
                        return redirect("profiles:upload_identity_document", field="face_photo")
                
                try:
                    # Parse base64 data
                    format_type, img_str = face_photo_data.split(";base64,")
                    ext = format_type.split("/")[-1]  # e.g., 'jpeg'
                    if ext not in ["jpg", "jpeg", "png"]:
                        if is_ajax(request):
                            return JsonResponse({
                                "success": False,
                                "errors": [{"field": None, "message": "Only JPG or PNG images are allowed."}]
                            }, status=400)
                        else:
                            messages.error(request, "Only JPG or PNG images are allowed.")
                            return redirect("profiles:upload_identity_document", field="face_photo")
                    
                    decoded_image = base64.b64decode(img_str)
                    if len(decoded_image) > 5 * 1024 * 1024:  # 5MB limit
                        if is_ajax(request):
                            return JsonResponse({
                                "success": False,
                                "errors": [{"field": None, "message": "Image file size must be under 5MB."}]
                            }, status=400)
                        else:
                            messages.error(request, "Image file size must be under 5MB.")
                            return redirect("profiles:upload_identity_document", field="face_photo")
                    
                    # Create ContentFile from base64 data
                    image_file = ContentFile(decoded_image, name=f"face_photo_{request.user.username}.{ext}")
                    uploaded_file = image_file
                    doc_type = doc_type_mapping[field]
                    
                except Exception as e:
                    logger.error(f"Error processing base64 face photo for {request.user.username}: {str(e)}")
                    if is_ajax(request):
                        return JsonResponse({
                            "success": False,
                            "errors": [{"field": None, "message": "Invalid image data. Please try capturing the photo again."}]
                        }, status=400)
                    else:
                        messages.error(request, "Invalid image data. Please try capturing the photo again.")
                        return redirect("profiles:upload_identity_document", field="face_photo")
            
            # Check if this is a regular file upload for face_photo
            elif "document_file" in request.FILES:
                uploaded_file = request.FILES["document_file"]
                doc_type = doc_type_mapping[field]
                
                # Validate file type for face_photo
                if uploaded_file.content_type not in ["image/jpeg", "image/png"]:
                    if is_ajax(request):
                        return JsonResponse({
                            "success": False,
                            "errors": [{"field": None, "message": "Face photo must be JPEG or PNG image."}]
                        }, status=400)
                    else:
                        return JsonResponse({
                            "success": False,
                            "errors": [{"field": None, "message": "Face photo must be JPEG or PNG image."}]
                        }, status=400)
            else:
                # No file or base64 data provided for face_photo
                if is_ajax(request):
                    return JsonResponse({
                        "success": False,
                        "errors": [{"field": None, "message": "No photo data provided. Please capture or upload a photo."}]
                    }, status=400)
                else:
                    messages.error(request, "No photo data provided. Please capture or upload a photo.")
                    return redirect("profiles:upload_identity_document", field="face_photo")
                
        else:
            # Handle regular file upload
            if "document_file" not in request.FILES:
                return JsonResponse(
                    {
                        "success": False,
                        "errors": [
                            {"field": None, "message": "No document file provided."}
                        ],
                    },
                    status=400,
                )

            uploaded_file = request.FILES["document_file"]
            doc_type = doc_type_mapping[field]

            # Validate file type for face_photo
            if field == "face_photo" and uploaded_file.content_type not in [
                "image/jpeg",
                "image/png",
            ]:
                return JsonResponse(
                    {
                        "success": False,
                        "errors": [
                            {
                                "field": None,
                                "message": "Face photo must be JPEG or PNG image.",
                            }
                        ],
                    },
                    status=400,
                )

        # Check if document already exists and update it, or create new one
        try:
            document = Document.objects.get(
                user=request.user,
                vehicle=None,  # Identity documents are user-only
                doc_type=doc_type,
            )
            # Update existing document
            document.file = uploaded_file
            document.save()

            # Reset review to pending - use get_or_create to prevent UNIQUE constraint issues
            review, created = DocumentReview.objects.get_or_create(
                document=document, defaults={"status": "PENDING"}
            )
            if not created:
                review.status = "PENDING"
                review.reviewed_by = None
                review.reviewed_at = None
                review.reason = ""
                review.save()

        except Document.DoesNotExist:
            # Create new document
            document = Document.objects.create(
                user=request.user,
                vehicle=None,  # Identity documents are user-only
                doc_type=doc_type,
                file=uploaded_file,
            )

            # Create review entry - use get_or_create to prevent UNIQUE constraint issues
            DocumentReview.objects.get_or_create(
                document=document, defaults={"status": "PENDING"}
            )

        logger.info(
            f"{field} uploaded by {request.user.username} as Document ID {document.id}"
        )

        # Send admin notification
        notify_admins(
            "document_uploaded",
            f"{request.user.username} uploaded {field.replace('_', ' ')}",
            {"field": field, "user_id": request.user.id, "document_id": document.id},
        )

        # Handle face_photo responses differently (from webcam capture or file upload)
        if field == "face_photo" and ("face_photo_data" in request.POST or request.FILES.get("document_file")):
            if is_ajax(request):
                return JsonResponse({
                    "success": True,
                    "message": "Face photo uploaded successfully! It's now being reviewed by our team.",
                    "redirect_url": reverse("profiles:profile")
                })
            else:
                messages.success(request, "Face photo uploaded successfully! It's now being reviewed by our team.")
                return redirect("profiles:profile")
        
        # Regular AJAX response for other documents
        return JsonResponse(
            {
                "success": True,
                "message": f'{field.replace("_", " ").title()} uploaded successfully.',
                "redirect_url": reverse("profiles:profile"),
            }
        )

    except Exception as e:
        logger.error(f"Error uploading {field} for {request.user.username}: {str(e)}")
        return JsonResponse(
            {
                "success": False,
                "errors": [
                    {"field": None, "message": f"Error uploading document: {str(e)}"}
                ],
            },
            status=500,
        )


@login_required
def edit_identity_document(request, field):
    """Edit an identity document."""
    valid_fields = ["id_card", "proof_of_residence", "face_photo"]
    if field not in valid_fields:
        return JsonResponse(
            {
                "success": False,
                "errors": [{"field": None, "message": "Invalid document field."}],
            },
            status=400,
        )

    # Map field names to Document doc_type values
    doc_type_mapping = {
        "id_card": "ID_CARD",
        "proof_of_residence": "PROOF_OF_RESIDENCE",
        "face_photo": "FACE_PHOTO",
    }

    try:
        from .models import Document, DocumentReview

        # Handle file upload
        if "document_file" not in request.FILES:
            return JsonResponse(
                {
                    "success": False,
                    "errors": [
                        {"field": None, "message": "No document file provided."}
                    ],
                },
                status=400,
            )

        uploaded_file = request.FILES["document_file"]
        doc_type = doc_type_mapping[field]

        # Validate file type for face_photo
        if field == "face_photo" and uploaded_file.content_type not in [
            "image/jpeg",
            "image/png",
        ]:
            return JsonResponse(
                {
                    "success": False,
                    "errors": [
                        {
                            "field": None,
                            "message": "Face photo must be JPEG or PNG image.",
                        }
                    ],
                },
                status=400,
            )

        # Check if document exists and update it
        try:
            document = Document.objects.get(
                user=request.user,
                vehicle=None,  # Identity documents are user-only
                doc_type=doc_type,
            )
            # Update existing document
            document.file = uploaded_file
            document.save()

            # Reset review to pending - use get_or_create to prevent UNIQUE constraint issues
            review, created = DocumentReview.objects.get_or_create(
                document=document, defaults={"status": "PENDING"}
            )
            if not created:
                review.status = "PENDING"
                review.reviewed_by = None
                review.reviewed_at = None
                review.reason = ""
                review.save()

        except Document.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "errors": [
                        {
                            "field": None,
                            "message": "Document not found. Please upload first.",
                        }
                    ],
                },
                status=404,
            )

        logger.info(
            f"{field} updated by {request.user.username} as Document ID {document.id}"
        )
        return JsonResponse(
            {
                "success": True,
                "message": f'{field.replace("_", " ").title()} updated successfully.',
                "redirect_url": reverse("profiles:profile"),
            }
        )

    except Exception as e:
        logger.error(f"Error updating {field} for {request.user.username}: {str(e)}")
        return JsonResponse(
            {
                "success": False,
                "errors": [
                    {"field": None, "message": f"Error updating document: {str(e)}"}
                ],
            },
            status=500,
        )


@login_required
def upload_face_photo(request):
    """Deprecated endpoint for face photo uploads."""
    return JsonResponse(
        {
            "success": False,
            "errors": "This endpoint is deprecated. Use upload_identity_document/face_photo/ instead.",
        },
        status=410,
    )


@login_required
def editProfile(request):
    """Handle editing of user profiles."""
    profile = request.user.profile

    if request.method == "POST":
        cropped_image_data = request.POST.get("cropped_image")
        if cropped_image_data:
            try:
                format, imgstr = cropped_image_data.split(";base64,")
                image_data = base64.b64decode(imgstr)
                image = Image.open(io.BytesIO(image_data))
                temp_buffer = io.BytesIO()
                image.save(temp_buffer, format="PNG")
                image_file = ContentFile(temp_buffer.getvalue())
                profile.profile_picture.save(
                    f"profile_pic_{request.user.username}.png", image_file, save=True
                )
            except Exception as e:
                messages.error(request, f"Error processing profile picture: {str(e)}")
                logger.error(
                    f"Profile picture processing failed for {request.user.username}: {str(e)}"
                )

        profile.first_name = request.POST.get("first_name", "")
        profile.middle_name = request.POST.get("middle_name", "")
        profile.last_name = request.POST.get("last_name", "")
        profile.bio = request.POST.get("bio", "")
        profile.title = request.POST.get("title", "")
        profile.gender = request.POST.get("gender", "O")
        profile.location = request.POST.get("location", "")
        profile.phone_number = request.POST.get("phone_number", "")
        profile.languages = request.POST.get("languages", "")
        try:
            profile.hourly_rate = Decimal(request.POST.get("hourly_rate", "0"))
        except (ValueError, TypeError):
            profile.hourly_rate = Decimal("0")
        profile.linkedin_profile = request.POST.get("linkedin_profile", "")
        profile.github_profile = request.POST.get("github_profile", "")
        profile.portfolio_link = request.POST.get("portfolio_link", "")
        profile.skills = request.POST.get("skills", "")
        try:
            profile.years_of_experience = int(
                request.POST.get("years_of_experience", 0)
            )
        except (ValueError, TypeError):
            profile.years_of_experience = 0
        profile.preferred_project_size = request.POST.get(
            "preferred_project_size", "ANY"
        )

        try:
            profile.save()
            messages.success(request, "Profile updated successfully!")
            logger.info(f"Profile updated for {request.user.username}")
        except Exception as e:
            messages.error(request, f"Error saving profile: {str(e)}")
            logger.error(f"Profile save failed for {request.user.username}: {str(e)}")

        return redirect("profiles:profile")

    return render(
        request,
        "profiles/edit_profile.html",
        {"user": request.user, "profile": profile},
    )


@login_required
def publicProfile(request, username):
    """Display a public view of a user's profile."""
    user = get_object_or_404(User, username=username)
    profile = user.profile
    experiences = profile.experiences.all().order_by("-start_date")
    education = profile.education.all().order_by("-start_date")
    portfolio_samples = Portfolio.objects.filter(user=user).order_by("-completion_date")
    average_rating = profile.get_average_rating()

    context = {
        "viewed_user": user,
        "profile": profile,
        "experiences": experiences,
        "education": education,
        "portfolio_samples": portfolio_samples,
        "average_rating": average_rating,
        "is_own_profile": (
            request.user == user if request.user.is_authenticated else False
        ),
    }

    logger.debug(f"Rendering public profile for {username}")
    return render(request, "profiles/public_profile.html", context)


@login_required
def add_education(request):
    """Handle adding new education entries."""
    if request.method != "POST":
        return redirect("profiles:profile")
        
    # Make a copy of POST data and set defaults for missing fields
    data = request.POST.copy()
    if "current" not in data:
        data["current"] = False

    form = EducationForm(data)
    if form.is_valid():
        education = form.save(commit=False)
        education.profile = request.user.profile  # Enforce ownership
        education.save()
        messages.success(request, "Education added successfully!")
        logger.info(f"Education added by {request.user.username}")
        return redirect("profiles:profile")
    else:
        logger.warning(
            f"Education form validation failed for {request.user.username}: {form.errors}"
        )
        messages.error(request, "Failed to add education. Please check the form and try again.")
        return redirect("profiles:profile")


@login_required
def add_portfolio(request):
    """Handle adding new portfolio entries."""
    if request.method != "POST":
        return redirect("profiles:profile")
        
    logger.debug(f"Portfolio POST data: {request.POST}, Files: {request.FILES}")
    portfolio_form = PortfolioForm(request.POST, request.FILES)
    sample_form = PortfolioSampleForm(request.POST, request.FILES)

    if portfolio_form.is_valid() and sample_form.is_valid():
        portfolio = portfolio_form.save(commit=False)
        portfolio.user = request.user  # Enforce ownership
        portfolio.save()

        sample = sample_form.save(commit=False)
        sample.portfolio = portfolio
        sample.completion_date = portfolio.completion_date
        sample.save()

        portfolio.sample = sample
        portfolio.save()

        messages.success(request, "Portfolio item added successfully!")
        logger.info(f"Portfolio added by {request.user.username}")
        return redirect("profiles:profile")
    else:
        errors = {}
        if portfolio_form.errors:
            errors.update(portfolio_form.errors)
        if sample_form.errors:
            errors.update(sample_form.errors)
        logger.warning(
            f"Portfolio form validation failed for {request.user.username}: {errors}"
        )
        messages.error(request, "Failed to add portfolio. Please check the form and try again.")
        return redirect("profiles:profile")


@login_required
def edit_portfolio(request, pk):
    """Edit portfolio with proper form instantiation."""
    if request.method != "POST":
        return redirect("profiles:profile")
        
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    
    logger.debug(f"Portfolio POST data: {request.POST}, Files: {request.FILES}")
    portfolio_form = PortfolioForm(request.POST, request.FILES, instance=portfolio)
    
    sample = portfolio.sample
    if not sample:
        sample = PortfolioSample(portfolio=portfolio)
        sample.save()
        
    sample_form = PortfolioSampleForm(request.POST, request.FILES, instance=sample)
    
    if portfolio_form.is_valid() and sample_form.is_valid():
        updated_portfolio = portfolio_form.save()
        updated_sample = sample_form.save(commit=False)
        updated_sample.portfolio = updated_portfolio
        updated_sample.completion_date = updated_portfolio.completion_date
        updated_sample.save()
        
        messages.success(request, "Portfolio updated successfully!")
        logger.info(f"Portfolio {pk} updated by {request.user.username}")
        return redirect("profiles:profile")
    else:
        errors = {}
        if portfolio_form.errors:
            errors.update(portfolio_form.errors)
        if sample_form.errors:
            errors.update(sample_form.errors)
        logger.warning(
            f"Portfolio update failed for {request.user.username}: {errors}"
        )
        messages.error(request, "Failed to update portfolio. Please check the form and try again.")
        return redirect("profiles:profile")


@login_required
def view_portfolio(request, pk):
    """Display portfolio details via JSON for AJAX requests."""
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    sample = portfolio.sample
    
    data = {
        "id": portfolio.id,
        "title": portfolio.title,
        "description": portfolio.description,
        "role": portfolio.role or "",
        "skills": portfolio.skills or "",
        "related_job": portfolio.related_job or "",
        "completion_date": portfolio.completion_date.strftime("%Y-%m-%d") if portfolio.completion_date else "",
        "image": portfolio.image.url if portfolio.image else "",
        "sample": (
            {
                "video": sample.video.url if sample and sample.video else "",
                "audio": sample.audio.url if sample and sample.audio else "",
                "pdf": sample.pdf.url if sample and sample.pdf else "",
                "url": sample.url or "",
                "text_block": sample.text_block or "",
            }
            if sample
            else None
        ),
    }
    
    logger.debug(f"Portfolio {pk} viewed by {request.user.username}")
    return JsonResponse({"ok": True, "data": data})


@login_required
def get_portfolio(request, pk):
    """Retrieve portfolio details for editing/viewing."""
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    sample = portfolio.sample
    data = {
        "id": portfolio.id,
        "title": portfolio.title,
        "description": portfolio.description,
        "role": portfolio.role or "",
        "skills": portfolio.skills or "",
        "related_job": portfolio.related_job or "",
        "completion_date": portfolio.completion_date.strftime("%Y-%m-%d") if portfolio.completion_date else "",
        "image": portfolio.image.url if portfolio.image else "",
        "sample": (
            {
                "video": sample.video.url if sample and sample.video else "",
                "audio": sample.audio.url if sample and sample.audio else "",
                "pdf": sample.pdf.url if sample and sample.pdf else "",
                "url": sample.url or "",
                "text_block": sample.text_block or "",
            }
            if sample
            else None
        ),
    }
    logger.debug(f"Portfolio {pk} retrieved for {request.user.username}")
    return JsonResponse({"ok": True, "data": data})


# Dashboard-specific operator assignment views
@login_required
def assign_operator_dashboard(request):
    """Assign operator via dashboard AJAX"""
    from .models import VehicleOwnership, OperatorAssignment

    if request.method == "POST":
        vehicle_id = request.POST.get("vehicle_id")
        operator_identifier = request.POST.get("operator_identifier", "").strip()

        if not vehicle_id or not operator_identifier:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Vehicle ID and operator identifier are required",
                },
                status=400,
            )

        try:
            vehicle = VehicleOwnership.objects.get(id=vehicle_id, owner=request.user)
        except VehicleOwnership.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Vehicle not found"}, status=404
            )

        # Find operator by username or email
        operator = None
        if "@" in operator_identifier:
            try:
                operator = User.objects.get(email=operator_identifier, is_active=True)
            except User.DoesNotExist:
                pass
        else:
            try:
                operator = User.objects.get(
                    username=operator_identifier, is_active=True
                )
            except User.DoesNotExist:
                pass

        if not operator:
            return JsonResponse(
                {
                    "success": False,
                    "errors": {"operator_identifier": ["User not found"]},
                },
                status=400,
            )

        # Check if operator is the same as owner
        if operator == request.user:
            return JsonResponse(
                {
                    "success": False,
                    "errors": {
                        "operator_identifier": ["Cannot assign yourself as operator"]
                    },
                },
                status=400,
            )

        # Check if operator has verified identity
        if not operator.profile.is_identity_verified:
            return JsonResponse(
                {
                    "success": False,
                    "errors": {
                        "operator_identifier": ["Operator must have verified identity"]
                    },
                },
                status=400,
            )

        # Check if operator is already assigned to this vehicle
        existing_assignment = OperatorAssignment.objects.filter(
            vehicle=vehicle, operator=operator, is_active=True
        ).first()

        if existing_assignment:
            return JsonResponse(
                {
                    "success": False,
                    "errors": {
                        "operator_identifier": [
                            "Operator is already assigned to this vehicle"
                        ]
                    },
                },
                status=400,
            )

        try:
            # Create new assignment
            assignment = OperatorAssignment.objects.create(
                vehicle=vehicle, operator=operator, assigned_by=request.user
            )

            logger.info(
                f"Operator {operator.username} assigned to vehicle {vehicle.plate_number} by {request.user.username}"
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Operator {operator.get_full_name() or operator.username} assigned successfully!",
                }
            )

        except Exception as e:
            logger.error(
                f"Error assigning operator {operator.username} to vehicle {vehicle_id}: {str(e)}"
            )
            return JsonResponse(
                {"success": False, "message": f"Error assigning operator: {str(e)}"},
                status=500,
            )

    return JsonResponse({"success": False, "message": "Invalid request"}, status=405)


@login_required
def remove_operator_dashboard(request):
    """Remove operator assignment via dashboard AJAX"""
    from .models import OperatorAssignment

    if request.method == "POST":
        assignment_id = request.POST.get("assignment_id")
        reason = request.POST.get("reason", "").strip()

        if not assignment_id:
            return JsonResponse(
                {"success": False, "message": "Assignment ID is required"}, status=400
            )

        try:
            assignment = OperatorAssignment.objects.get(
                id=assignment_id, vehicle__owner=request.user, is_active=True
            )
        except OperatorAssignment.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Assignment not found"}, status=404
            )

        try:
            # Deactivate assignment
            assignment.is_active = False
            assignment.deactivated_at = timezone.now()
            assignment.deactivated_by = request.user
            assignment.deactivation_reason = reason
            assignment.save()

            logger.info(
                f"Operator {assignment.operator.username} removed from vehicle {assignment.vehicle.plate_number} by {request.user.username}"
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Operator {assignment.operator.get_full_name() or assignment.operator.username} removed successfully!",
                }
            )

        except Exception as e:
            logger.error(
                f"Error removing operator assignment {assignment_id}: {str(e)}"
            )
            return JsonResponse(
                {"success": False, "message": f"Error removing operator: {str(e)}"},
                status=500,
            )

    return JsonResponse({"success": False, "message": "Invalid request"}, status=405)


@login_required
def operator_dashboard(request):
    """Dashboard for operators to see their assigned vehicles"""
    from .models import OperatorAssignment, Document, VehicleOwnership

    # Get all active assignments for this operator
    active_assignments = (
        OperatorAssignment.objects.filter(operator=request.user, is_active=True)
        .select_related("vehicle", "vehicle__owner", "assigned_by")
        .order_by("-assigned_at")
    )

    # Get operator's driver license status
    driver_license_status = "MISSING"
    driver_license_doc = None
    try:
        driver_license_doc = Document.objects.get(
            user=request.user, doc_type="DRIVER_LICENSE", vehicle__isnull=True
        )
        if hasattr(driver_license_doc, "review"):
            driver_license_status = driver_license_doc.review.status
        else:
            driver_license_status = "PENDING"
    except Document.DoesNotExist:
        pass

    # Prepare vehicles data with document status
    vehicles_data = []
    for assignment in active_assignments:
        vehicle = assignment.vehicle

        # Get vehicle documents status
        required_docs = vehicle.get_required_documents()
        docs_status = []
        for doc_type in required_docs:
            docs_status.append(
                {
                    "type": doc_type,
                    "display": dict(Document.DOC_TYPE_CHOICES)[doc_type],
                    "status": vehicle.get_document_status(doc_type),
                }
            )

        vehicles_data.append(
            {
                "assignment": assignment,
                "vehicle": vehicle,
                "owner": vehicle.owner,
                "documents": docs_status,
                "is_fully_documented": vehicle.is_fully_documented(),
            }
        )

    # Get assignment history
    assignment_history = (
        OperatorAssignment.objects.filter(operator=request.user, is_active=False)
        .select_related("vehicle", "vehicle__owner", "assigned_by", "deactivated_by")
        .order_by("-deactivated_at")[:10]
    )  # Last 10 inactive assignments

    context = {
        "active_assignments": active_assignments,
        "vehicles_data": vehicles_data,
        "assignment_history": assignment_history,
        "driver_license_status": driver_license_status,
        "driver_license_doc": driver_license_doc,
        "total_active_vehicles": active_assignments.count(),
        "is_identity_verified": request.user.profile.is_identity_verified,
    }

    return render(request, "profiles/operator_dashboard.html", context)


@login_required
def add_skill(request):
    """Handle adding new skill entries."""
    if (
        request.method == "POST"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        try:
            skill_name = request.POST.get("skill_name")
            skill_category = request.POST.get("skill_category", "General")
            proficiency = request.POST.get("proficiency")
            years_of_experience = request.POST.get("years_of_experience", 0)

            if not skill_name or not proficiency:
                return JsonResponse(
                    {
                        "success": False,
                        "errors": {
                            "skill_name": ["Skill name and proficiency are required"]
                        },
                    }
                )

            # Get or create skill
            skill, created = Skill.objects.get_or_create(
                name=skill_name, defaults={"category": skill_category}
            )

            # Check if user already has this skill
            if ProfileSkill.objects.filter(
                profile=request.user.profile, skill=skill
            ).exists():
                return JsonResponse(
                    {
                        "success": False,
                        "errors": {
                            "skill_name": [
                                "You already have this skill in your profile"
                            ]
                        },
                    }
                )

            # Create profile skill
            profile_skill = ProfileSkill.objects.create(
                profile=request.user.profile,
                skill=skill,
                proficiency=proficiency,
                years_of_experience=(
                    int(years_of_experience) if years_of_experience else 0
                ),
            )

            messages.success(request, "Skill added successfully!")
            logger.info(f"Skill {skill_name} added by {request.user.username}")
            return JsonResponse({"success": True})

        except Exception as e:
            logger.error(f"Error adding skill for {request.user.username}: {str(e)}")
            return JsonResponse(
                {
                    "success": False,
                    "errors": {"general": ["An error occurred while adding the skill"]},
                }
            )
    else:
        logger.warning(f"Invalid skill request by {request.user.username}")
        return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def update_skill(request):
    """Handle updating skill entries."""
    if (
        request.method == "POST"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        skill_id = request.POST.get("id")
        if not skill_id:
            logger.warning(f"Missing skill ID for update by {request.user.username}")
            return JsonResponse(
                {"success": False, "error": "Missing skill ID"}, status=400
            )

        profile_skill = get_object_or_404(
            ProfileSkill, id=skill_id, profile=request.user.profile
        )

        try:
            skill_name = request.POST.get("skill_name")
            skill_category = request.POST.get("skill_category", "General")
            proficiency = request.POST.get("proficiency")
            years_of_experience = request.POST.get("years_of_experience", 0)

            if not skill_name or not proficiency:
                return JsonResponse(
                    {
                        "success": False,
                        "errors": {
                            "skill_name": ["Skill name and proficiency are required"]
                        },
                    }
                )

            # Get or create skill
            skill, created = Skill.objects.get_or_create(
                name=skill_name, defaults={"category": skill_category}
            )

            # Check if user already has this skill (excluding current one)
            if (
                ProfileSkill.objects.filter(profile=request.user.profile, skill=skill)
                .exclude(id=skill_id)
                .exists()
            ):
                return JsonResponse(
                    {
                        "success": False,
                        "errors": {
                            "skill_name": [
                                "You already have this skill in your profile"
                            ]
                        },
                    }
                )

            # Update profile skill
            profile_skill.skill = skill
            profile_skill.proficiency = proficiency
            profile_skill.years_of_experience = (
                int(years_of_experience) if years_of_experience else 0
            )
            profile_skill.save()

            messages.success(request, "Skill updated successfully!")
            logger.info(f"Skill {skill_name} updated by {request.user.username}")
            return JsonResponse({"success": True})

        except Exception as e:
            logger.error(f"Error updating skill for {request.user.username}: {str(e)}")
            return JsonResponse(
                {
                    "success": False,
                    "errors": {
                        "general": ["An error occurred while updating the skill"]
                    },
                }
            )
    else:
        logger.warning(f"Invalid skill update request by {request.user.username}")
        return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def get_skill(request, skill_id):
    """Retrieve skill details for editing."""
    profile_skill = get_object_or_404(
        ProfileSkill, id=skill_id, profile=request.user.profile
    )
    logger.debug(f"Skill {skill_id} retrieved for {request.user.username}")
    return JsonResponse(
        {
            "id": profile_skill.id,
            "skill_name": profile_skill.skill.name,
            "skill_category": profile_skill.skill.category,
            "proficiency": profile_skill.proficiency,
            "years_of_experience": profile_skill.years_of_experience,
        }
    )


@login_required
def update_education(request):
    """Handle updating education entries."""
    if request.method != "POST":
        return redirect("profiles:profile")
        
    edu_id = request.POST.get("id")
    if not edu_id:
        return JsonResponse({"ok": False, "error": "Missing education ID"}, status=400)

    education = get_object_or_404(Education, id=edu_id, profile=request.user.profile)

    # Make a copy of POST data and set defaults for missing fields
    data = request.POST.copy()
    if "current" not in data:
        data["current"] = False

    form = EducationForm(data, instance=education)
    if form.is_valid():
        updated_education = form.save()
        messages.success(request, "Education updated successfully!")
        logger.info(f"Education {edu_id} updated by {request.user.username}")
        return redirect("profiles:profile")
    else:
        logger.warning(
            f"Education update failed for {request.user.username}: {form.errors}"
        )
        messages.error(request, "Failed to update education. Please check the form and try again.")
        return redirect("profiles:profile")


@login_required
def get_education(request, edu_id):
    """Retrieve education details for editing."""
    education = get_object_or_404(Education, id=edu_id, profile=request.user.profile)
    logger.debug(f"Education {edu_id} retrieved for {request.user.username}")
    return JsonResponse({
        "ok": True,
        "data": {
            "id": education.id,
            "institution": education.institution,
            "degree": education.degree,
            "field_of_study": education.field_of_study,
            "start_date": education.start_date.strftime("%Y-%m-%d"),
            "end_date": (
                education.end_date.strftime("%Y-%m-%d") if education.end_date else None
            ),
            "current": education.current,
            "description": education.description,
        }
    })


@login_required
def add_experience(request):
    """Handle adding new experience entries."""
    if request.method != "POST":
        return redirect("profiles:profile")
        
    # Make a copy of POST data and set defaults for missing fields
    data = request.POST.copy()
    if "location" not in data:
        data["location"] = ""
    if "current" not in data:
        data["current"] = False

    form = ExperienceForm(data)
    if form.is_valid():
        experience = form.save(commit=False)
        experience.profile = request.user.profile  # Enforce ownership
        experience.save()
        messages.success(request, "Experience added successfully!")
        logger.info(f"Experience added by {request.user.username}")
        return redirect("profiles:profile")
    else:
        logger.warning(
            f"Experience form validation failed for {request.user.username}: {form.errors}"
        )
        messages.error(request, "Failed to add experience. Please check the form and try again.")
        return redirect("profiles:profile")


@login_required
def update_experience(request):
    """Handle updating experience entries."""
    if request.method != "POST":
        return redirect("profiles:profile")
        
    exp_id = request.POST.get("id")
    if not exp_id:
        return JsonResponse({"ok": False, "error": "Missing experience ID"}, status=400)
        
    experience = get_object_or_404(Experience, id=exp_id, profile=request.user.profile)
    
    # Make a copy of POST data and set defaults for missing fields
    data = request.POST.copy()
    if "location" not in data:
        data["location"] = ""
    if "current" not in data:
        data["current"] = False
        
    form = ExperienceForm(data, instance=experience)
    if form.is_valid():
        updated_experience = form.save()
        messages.success(request, "Experience updated successfully!")
        logger.info(f"Experience {exp_id} updated by {request.user.username}")
        return redirect("profiles:profile")
    else:
        logger.warning(
            f"Experience update failed for {request.user.username}: {form.errors}"
        )
        messages.error(request, "Failed to update experience. Please check the form and try again.")
        return redirect("profiles:profile")


@login_required
def get_experience(request, exp_id):
    """Retrieve experience details for editing."""
    experience = get_object_or_404(Experience, id=exp_id, profile=request.user.profile)
    logger.debug(f"Experience {exp_id} retrieved for {request.user.username}")
    return JsonResponse({
        "ok": True,
        "data": {
            "id": experience.id,
            "title": experience.title,
            "company": experience.company,
            "location": experience.location or "",
            "start_date": experience.start_date.strftime("%Y-%m-%d"),
            "end_date": (
                experience.end_date.strftime("%Y-%m-%d")
                if experience.end_date
                else None
            ),
            "current": experience.current,
            "description": experience.description or "",
        }
    })


@login_required
def delete_experience(request, pk):
    """Handle deleting an experience entry."""
    experience = get_object_or_404(Experience, pk=pk, profile=request.user.profile)
    if request.method == "POST":
        experience.delete()
        messages.success(request, "Experience deleted successfully!")
        logger.info(f"Experience {pk} deleted by {request.user.username}")
        return redirect("profiles:profile")
    elif request.method == "GET":
        # Return experience data for confirmation dialog
        return JsonResponse({
            "ok": True,
            "data": {
                "id": experience.id,
                "title": experience.title,
                "company": experience.company
            }
        })
    else:
        return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)


@login_required
def delete_education(request, pk):
    """Handle deleting an education entry."""
    education = get_object_or_404(Education, pk=pk, profile=request.user.profile)
    if request.method == "POST":
        education.delete()
        messages.success(request, "Education deleted successfully!")
        logger.info(f"Education {pk} deleted by {request.user.username}")
        return redirect("profiles:profile")
    elif request.method == "GET":
        # Return education data for confirmation dialog
        return JsonResponse({
            "ok": True,
            "data": {
                "id": education.id,
                "institution": education.institution,
                "degree": education.degree
            }
        })
    else:
        return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)


@login_required
def delete_portfolio(request, pk):
    """Handle deleting a portfolio item."""
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    if request.method == "POST":
        portfolio.delete()
        messages.success(request, "Portfolio item deleted successfully!")
        logger.info(f"Portfolio {pk} deleted by {request.user.username}")
        return redirect("profiles:profile")
    elif request.method == "GET":
        # Return portfolio data for confirmation dialog
        return JsonResponse({
            "ok": True,
            "data": {
                "id": portfolio.id,
                "title": portfolio.title,
                "description": portfolio.description
            }
        })
    else:
        return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)


@login_required
def delete_skill(request, pk):
    """Handle deleting a skill."""
    skill = get_object_or_404(ProfileSkill, pk=pk, profile=request.user.profile)
    if request.method == "POST":
        skill.delete()
        messages.success(request, "Skill deleted successfully!")
        logger.info(f"Skill {pk} deleted by {request.user.username}")
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return redirect("profiles:profile")
    return render(request, "profiles/delete_skill.html", {"skill": skill})


@login_required
def update_availability(request):
    """Handle updating availability status."""
    availability, created = Availability.objects.get_or_create(
        profile=request.user.profile
    )

    if request.method == "POST":
        form = AvailabilityForm(request.POST, instance=availability)
        if form.is_valid():
            form.save()
            messages.success(request, "Availability updated successfully!")
            logger.info(f"Availability updated by {request.user.username}")
            return redirect("profiles:profile")
        else:
            messages.error(request, "Please correct the errors below.")
            logger.warning(
                f"Availability update failed for {request.user.username}: {form.errors}"
            )
    else:
        form = AvailabilityForm(instance=availability)

    return render(request, "profiles/availability_form.html", {"form": form})


def fetch_notifications(request):
    """Fetch user notifications."""
    if request.user.is_authenticated:
        from notifications.models import Notification

        notifications = Notification.objects.filter(user=request.user).order_by(
            "-created_at"
        )
        new_count = notifications.filter(is_read=False).count()
        notifications_data = [
            {
                "id": notif.id,
                "message": notif.message,
                "created_at": notif.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "is_read": notif.is_read,
            }
            for notif in notifications
        ]
        logger.debug(f"Notifications fetched for {request.user.username}")
        return JsonResponse(
            {"notifications": notifications_data, "new_count": new_count}
        )
    logger.warning("Unauthorized notification fetch attempt")
    return JsonResponse({"error": "Unauthorized"}, status=401)


def mark_all_as_read(request):
    """Mark all notifications as read."""
    if request.user.is_authenticated:
        from notifications.models import Notification

        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True
        )
        logger.info(f"All notifications marked as read for {request.user.username}")
        return JsonResponse({"message": "All notifications marked as read"})
    logger.warning("Unauthorized mark all as read attempt")
    return JsonResponse({"error": "Unauthorized"}, status=401)


# OTP-based verification views
def verify_account(request):
    """Handle account verification with OTP."""
    user_id = request.session.get("otp_user_id")
    if not user_id:
        messages.error(request, "No verification session found. Please register again.")
        return redirect("profiles:register")

    try:
        user = User.objects.get(id=user_id, is_active=False)
    except User.DoesNotExist:
        messages.error(request, "Invalid verification session. Please register again.")
        return redirect("profiles:register")

    if request.method == "POST":
        otp_code = request.POST.get("otp_code", "").strip()
        if not otp_code:
            messages.error(request, "Please enter the verification code.")
        else:
            success, message = OTPService.verify_otp(user, otp_code, "VERIFY")
            if success:
                # Clean up session
                del request.session["otp_user_id"]
                # Log user in
                login(
                    request, user, backend="django.contrib.auth.backends.ModelBackend"
                )
                messages.success(
                    request, "Account verified successfully! Welcome to LusitoHub."
                )
                logger.info(f"Account verified for user {user.username}")
                return redirect("profiles:profile")
            else:
                messages.error(request, message)

    # Check if user can request resend
    can_resend, cooldown_remaining = OTPService.can_resend_otp(user, "VERIFY")

    context = {
        "user": user,
        "user_email": user.email,
        "masked_email": f"{user.email[:2]}{'*' * (len(user.email) - 6)}{user.email[-4:]}",
        "can_resend": can_resend,
        "cooldown_remaining": cooldown_remaining,
    }

    return render(request, "profiles/verify.html", context)


def resend_account_otp(request):
    """Resend OTP for account verification."""
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Invalid request method."}, status=405
        )

    user_id = request.session.get("otp_user_id")
    if not user_id:
        return JsonResponse(
            {"success": False, "message": "No verification session found."}, status=400
        )

    try:
        user = User.objects.get(id=user_id, is_active=False)
    except User.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Invalid verification session."}, status=400
        )

    can_resend, cooldown_remaining = OTPService.can_resend_otp(user, "VERIFY")
    if not can_resend:
        return JsonResponse(
            {
                "success": False,
                "message": f"Please wait {cooldown_remaining} seconds before requesting another code.",
                "cooldown_remaining": cooldown_remaining,
            },
            status=429,
        )

    # Get preferred channel from request or default to EMAIL
    preferred_channel = request.POST.get("resend_channel", "EMAIL")
    available_channels = OTPService.get_available_channels(user)

    if preferred_channel not in available_channels:
        preferred_channel = "EMAIL"

    otp = OTPService.create_otp(user, "VERIFY", preferred_channel)
    if otp:
        logger.info(f"Verification OTP resent to {user.email}")
        return JsonResponse(
            {
                "success": True,
                "message": "Verification code sent! Please check your email.",
                "cooldown_remaining": 60,
            }
        )
    else:
        return JsonResponse(
            {
                "success": False,
                "message": "Failed to send verification code. Please try again later.",
            },
            status=500,
        )


def reset_request(request):
    """Handle password reset request."""
    if request.method == "POST":
        email_or_username = request.POST.get("email_or_username", "").strip()
        if not email_or_username:
            messages.error(request, "Please enter your email or username.")
        else:
            # Try to find user by email or username
            user = None
            if "@" in email_or_username:
                try:
                    user = User.objects.get(email=email_or_username, is_active=True)
                except User.DoesNotExist:
                    pass
            else:
                try:
                    user = User.objects.get(username=email_or_username, is_active=True)
                except User.DoesNotExist:
                    pass

            if user:
                # Check if user can request reset
                can_resend, cooldown_remaining = OTPService.can_resend_otp(
                    user, "RESET"
                )
                if not can_resend:
                    messages.error(
                        request,
                        f"Please wait {cooldown_remaining} seconds before requesting another reset code.",
                    )
                else:
                    # Get preferred channel or use email + SMS if available
                    preferred_channel = request.POST.get("otp_channel", "EMAIL")
                    available_channels = OTPService.get_available_channels(user)

                    # If BOTH is requested and SMS is available, use BOTH
                    if preferred_channel == "BOTH" and "SMS" in available_channels:
                        channel = "BOTH"
                    elif preferred_channel == "SMS" and "SMS" in available_channels:
                        channel = "SMS"
                    else:
                        channel = "EMAIL"

                    otp = OTPService.create_otp(user, "RESET", channel)
                    if otp:
                        request.session["reset_user_id"] = user.id
                        messages.success(
                            request, "Reset code sent! Please check your email."
                        )
                        logger.info(f"Password reset OTP sent to {user.email}")
                        return redirect("profiles:reset_verify")
                    else:
                        messages.error(
                            request,
                            "Failed to send reset code. Please try again later.",
                        )
            else:
                # Don't reveal if user exists or not for security
                messages.info(
                    request,
                    "If an account with that email/username exists, you'll receive a reset code shortly.",
                )

    return render(request, "profiles/reset_request.html")


def reset_verify(request):
    """Handle password reset OTP verification."""
    user_id = request.session.get("reset_user_id")
    if not user_id:
        messages.error(
            request, "No reset session found. Please request a password reset again."
        )
        return redirect("profiles:reset_request")

    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        messages.error(
            request, "Invalid reset session. Please request a password reset again."
        )
        return redirect("profiles:reset_request")

    if request.method == "POST":
        otp_code = request.POST.get("otp_code", "").strip()
        if not otp_code:
            messages.error(request, "Please enter the reset code.")
        else:
            success, message = OTPService.verify_otp(user, otp_code, "RESET")
            if success:
                request.session["reset_verified"] = True
                messages.success(
                    request, "Reset code verified! You can now set a new password."
                )
                logger.info(f"Password reset OTP verified for user {user.username}")
                return redirect("profiles:reset_new_password")
            else:
                messages.error(request, message)

    # Check if user can request resend
    can_resend, cooldown_remaining = OTPService.can_resend_otp(user, "RESET")

    context = {
        "user": user,
        "user_email": user.email,
        "masked_email": f"{user.email[:2]}{'*' * (len(user.email) - 6)}{user.email[-4:]}",
        "can_resend": can_resend,
        "cooldown_remaining": cooldown_remaining,
    }

    return render(request, "profiles/reset_verify.html", context)


def resend_reset_otp(request):
    """Resend OTP for password reset."""
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Invalid request method."}, status=405
        )

    user_id = request.session.get("reset_user_id")
    if not user_id:
        return JsonResponse(
            {"success": False, "message": "No reset session found."}, status=400
        )

    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Invalid reset session."}, status=400
        )

    can_resend, cooldown_remaining = OTPService.can_resend_otp(user, "RESET")
    if not can_resend:
        return JsonResponse(
            {
                "success": False,
                "message": f"Please wait {cooldown_remaining} seconds before requesting another code.",
                "cooldown_remaining": cooldown_remaining,
            },
            status=429,
        )

    # Get preferred channel from request
    preferred_channel = request.POST.get("resend_channel", "EMAIL")
    available_channels = OTPService.get_available_channels(user)

    if preferred_channel not in available_channels:
        preferred_channel = "EMAIL"

    otp = OTPService.create_otp(user, "RESET", preferred_channel)
    if otp:
        logger.info(f"Password reset OTP resent to {user.email}")
        return JsonResponse(
            {
                "success": True,
                "message": "Reset code sent! Please check your email.",
                "cooldown_remaining": 60,
            }
        )
    else:
        return JsonResponse(
            {
                "success": False,
                "message": "Failed to send reset code. Please try again later.",
            },
            status=500,
        )


def reset_new_password(request):
    """Handle setting new password after OTP verification."""
    user_id = request.session.get("reset_user_id")
    reset_verified = request.session.get("reset_verified")

    if not user_id or not reset_verified:
        messages.error(
            request,
            "Invalid reset session. Please start the password reset process again.",
        )
        return redirect("profiles:reset_request")

    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        messages.error(
            request,
            "Invalid reset session. Please start the password reset process again.",
        )
        return redirect("profiles:reset_request")

    if request.method == "POST":
        password1 = request.POST.get("password1", "").strip()
        password2 = request.POST.get("password2", "").strip()

        if not password1 or not password2:
            messages.error(request, "Please fill in both password fields.")
        elif password1 != password2:
            messages.error(request, "Passwords do not match.")
        elif len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
        else:
            user.set_password(password1)
            user.save()

            # Clean up session
            del request.session["reset_user_id"]
            del request.session["reset_verified"]

            messages.success(
                request,
                "Password updated successfully! You can now log in with your new password.",
            )
            logger.info(f"Password reset completed for user {user.username}")
            return redirect("login")

    context = {
        "user": user,
    }

    return render(request, "profiles/reset_new_password.html", context)


# Vehicle Dashboard Views (New Workflow)
@login_required
def vehicle_dashboard(request):
    """Main vehicle dashboard showing user's vehicles and documents"""
    from .models import (
        VehicleOwnership,
        Document,
        DocumentReview,
        OperatorAssignment,
        TransportOwnerBadge,
    )
    from .forms import VehicleOwnershipForm, DocumentForm, OperatorAssignmentForm

    # Get user's vehicles with operator assignments
    vehicles = VehicleOwnership.objects.filter(owner=request.user).prefetch_related(
        "operator_assignment__operator"
    )

    # Get user's driver license status
    driver_license_status = "MISSING"
    driver_license_doc = None
    try:
        driver_license_doc = Document.objects.get(
            user=request.user, doc_type="DRIVER_LICENSE", vehicle__isnull=True
        )
        driver_license_status = (
            driver_license_doc.review.status
            if hasattr(driver_license_doc, "review")
            else "PENDING"
        )
    except Document.DoesNotExist:
        pass

    # Get permit status and badge info
    current_permit = None
    permit_status = "MISSING"
    rejection_reason = None

    try:
        current_permit = (
            Document.objects.filter(
                user=request.user, doc_type="PERMIT", vehicle__isnull=True
            )
            .select_related("review")
            .latest("uploaded_at")
        )

        if hasattr(current_permit, "review") and current_permit.review:
            permit_status = current_permit.review.status
            if current_permit.review.status == "REJECTED":
                rejection_reason = current_permit.review.reason
        else:
            permit_status = "PENDING"

    except Document.DoesNotExist:
        pass

    # Get or create transport owner badge
    badge, created = TransportOwnerBadge.objects.get_or_create(
        user=request.user, defaults={"authorized": False}
    )

    # Get referral statistics
    from .services.referral import ReferralService

    referral_stats = ReferralService.get_referral_stats(request.user)

    # Forms for modals
    vehicle_form = VehicleOwnershipForm()
    document_form = DocumentForm()
    driver_license_form = DocumentForm(vehicle=None)  # For driver license only
    # Don't create operator assignment form without a vehicle
    operator_assignment_form = None

    context = {
        "vehicles": vehicles,
        "driver_license_status": driver_license_status,
        "driver_license_doc": driver_license_doc,
        "permit_status": permit_status,
        "current_permit": current_permit,
        "rejection_reason": rejection_reason,
        "is_authorized_provider": badge.authorized,
        "vehicle_form": vehicle_form,
        "document_form": document_form,
        "driver_license_form": driver_license_form,
        "operator_assignment_form": operator_assignment_form,
        "referral_stats": referral_stats,
    }

    return render(request, "profiles/vehicle_dashboard.html", context)


@login_required
def add_vehicle_dashboard(request):
    """Add new vehicle via AJAX"""
    from .forms import VehicleOwnershipForm
    from .models import VehicleOwnership, OperatorAssignment

    if request.method == "POST":
        form = VehicleOwnershipForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.owner = request.user
            vehicle.save()

            # Handle operator assignment if checkbox was checked
            will_be_operator = form.cleaned_data.get("will_be_operator", False)

            if will_be_operator:
                # Check if user has an active assignment to another vehicle
                existing_assignment = OperatorAssignment.objects.filter(
                    operator=request.user, active=True
                ).first()

                if existing_assignment:
                    # Deactivate the existing assignment
                    existing_assignment.active = False
                    existing_assignment.deactivated_at = timezone.now()
                    existing_assignment.save()

                    logger.info(
                        f"Deactivated existing operator assignment for {request.user.username} from vehicle {existing_assignment.vehicle.plate_number}"
                    )

                # Create new operator assignment
                OperatorAssignment.objects.create(
                    vehicle=vehicle,
                    operator=request.user,
                    assigned_by=request.user,
                    active=True,
                )

                logger.info(
                    f"Vehicle {vehicle.plate_number} added with owner {request.user.username} as operator"
                )
            else:
                logger.info(
                    f"Vehicle {vehicle.plate_number} added by {request.user.username} without operator assignment"
                )

            # Update transport owner tag if needed
            request.user.profile.update_transport_owner_tag()

            message = "Vehicle added successfully!"
            if will_be_operator:
                message += " You have been assigned as the operator."

            return JsonResponse(
                {
                    "success": True,
                    "message": message,
                    "vehicle": {
                        "id": vehicle.id,
                        "plate_number": vehicle.plate_number,
                        "make": vehicle.make,
                        "model": vehicle.model,
                        "year": vehicle.year,
                        "vehicle_type": (
                            vehicle.get_vehicle_type_display()
                            if vehicle.vehicle_type
                            else ""
                        ),
                        "has_operator": will_be_operator,
                    },
                }
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)

    return JsonResponse({"success": False, "message": "Invalid request"}, status=405)


@login_required
def upload_document_dashboard(request):
    """Upload document via AJAX"""
    from .forms import DocumentForm
    from .models import VehicleOwnership, Document, DocumentReview

    if request.method == "POST":
        vehicle_id = request.POST.get("vehicle_id")
        vehicle = None

        if vehicle_id and vehicle_id != "null":
            try:
                vehicle = VehicleOwnership.objects.get(
                    id=vehicle_id, owner=request.user
                )
            except VehicleOwnership.DoesNotExist:
                return JsonResponse(
                    {"success": False, "message": "Vehicle not found"}, status=404
                )

        form = DocumentForm(request.POST, request.FILES, vehicle=vehicle)

        if form.is_valid():
            # Check if document already exists and replace it
            doc_type = form.cleaned_data["doc_type"]
            try:
                existing_doc = Document.objects.get(
                    user=request.user, vehicle=vehicle, doc_type=doc_type
                )
                # Delete old file and review
                if existing_doc.file:
                    existing_doc.file.delete()
                if hasattr(existing_doc, "review"):
                    existing_doc.review.delete()
                existing_doc.delete()

                logger.info(
                    f"Replaced existing {doc_type} document for user {request.user.username}"
                )
            except Document.DoesNotExist:
                pass

            # Save new document
            document = form.save(user=request.user, vehicle=vehicle)

            logger.info(f"Document {doc_type} uploaded by {request.user.username}")

            return JsonResponse(
                {
                    "success": True,
                    "message": f"{document.get_doc_type_display()} uploaded successfully! Awaiting review.",
                    "document": {
                        "id": document.id,
                        "doc_type": document.doc_type,
                        "doc_type_display": document.get_doc_type_display(),
                        "status": "PENDING",
                        "uploaded_at": document.uploaded_at.strftime("%Y-%m-%d %H:%M"),
                    },
                }
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)

    return JsonResponse({"success": False, "message": "Invalid request"}, status=405)


@login_required
def get_vehicle_documents(request, vehicle_id):
    """Get documents for a specific vehicle via AJAX"""
    from .models import VehicleOwnership, Document

    try:
        vehicle = VehicleOwnership.objects.get(id=vehicle_id, owner=request.user)
    except VehicleOwnership.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Vehicle not found"}, status=404
        )

    documents = []
    required_docs = vehicle.get_required_documents()

    for doc_type in required_docs:
        doc_info = {
            "doc_type": doc_type,
            "doc_type_display": dict(Document.DOC_TYPE_CHOICES)[doc_type],
            "status": vehicle.get_document_status(doc_type),
            "uploaded": False,
            "uploaded_at": None,
            "rejection_reason": None,
        }

        try:
            document = Document.objects.get(vehicle=vehicle, doc_type=doc_type)
            doc_info.update(
                {
                    "uploaded": True,
                    "uploaded_at": document.uploaded_at.strftime("%Y-%m-%d %H:%M"),
                    "file_url": document.file.url if document.file else None,
                }
            )

            if hasattr(document, "review") and document.review.reason:
                doc_info["rejection_reason"] = document.review.reason

        except Document.DoesNotExist:
            pass

        documents.append(doc_info)

    return JsonResponse(
        {
            "success": True,
            "documents": documents,
            "vehicle": {
                "id": vehicle.id,
                "plate_number": vehicle.plate_number,
                "display_name": str(vehicle),
            },
        }
    )


@login_required
def delete_vehicle_dashboard(request, vehicle_id):
    """Delete vehicle via AJAX"""
    from .models import VehicleOwnership

    if request.method == "DELETE":
        try:
            vehicle = VehicleOwnership.objects.get(id=vehicle_id, owner=request.user)
            plate_number = vehicle.plate_number

            # Delete associated documents
            vehicle.generic_documents.all().delete()
            vehicle.delete()

            logger.info(f"Vehicle {plate_number} deleted by {request.user.username}")

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Vehicle {plate_number} deleted successfully!",
                }
            )
        except VehicleOwnership.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Vehicle not found"}, status=404
            )

    return JsonResponse({"success": False, "message": "Invalid request"}, status=405)


# Operator Assignment Views
@login_required
def assign_vehicle_operator(request, vehicle_id):
    """Assign an operator to a vehicle using the new OperatorAssignment model"""
    from .models import VehicleOwnership

    try:
        vehicle = VehicleOwnership.objects.get(id=vehicle_id, owner=request.user)
    except VehicleOwnership.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Vehicle not found or you do not have permission to assign operators",
            },
            status=404,
        )

    if request.method == "POST":
        form = OperatorAssignmentForm(request.POST, vehicle=vehicle)

        if form.is_valid():
            try:
                assignment = form.save(assigned_by=request.user)

                logger.info(
                    f"Operator {assignment.operator.username} assigned to vehicle "
                    f"{vehicle.plate_number} by {request.user.username}"
                )

                return JsonResponse(
                    {
                        "success": True,
                        "message": f"Operator {assignment.operator.get_full_name() or assignment.operator.username} "
                        f"has been assigned to vehicle {vehicle.plate_number}",
                        "assignment": {
                            "id": assignment.id,
                            "operator_username": assignment.operator.username,
                            "operator_name": assignment.operator.get_full_name()
                            or assignment.operator.username,
                            "assigned_at": assignment.assigned_at.strftime(
                                "%Y-%m-%d %H:%M"
                            ),
                            "is_active": assignment.is_active,
                        },
                    }
                )

            except Exception as e:
                logger.error(
                    f"Error creating operator assignment for vehicle {vehicle_id} "
                    f"by {request.user.username}: {str(e)}"
                )
                return JsonResponse(
                    {
                        "success": False,
                        "message": f"Error creating assignment: {str(e)}",
                    },
                    status=500,
                )
        else:
            # Build consistent error format like other AJAX endpoints
            errors = [
                {"field": field, "message": msg}
                for field, errors_list in form.errors.items()
                for msg in errors_list
            ]
            return JsonResponse({"success": False, "errors": errors}, status=400)

    # GET request - show form
    form = OperatorAssignmentForm(vehicle=vehicle)

    context = {
        "vehicle": vehicle,
        "form": form,
        "existing_assignments": OperatorAssignment.objects.filter(
            vehicle=vehicle, is_active=True
        ).select_related("operator"),
    }

    return render(request, "profiles/assign_operator.html", context)


@login_required
def deactivate_vehicle_operator(request, assignment_id):
    """Deactivate an operator assignment"""
    try:
        assignment = OperatorAssignment.objects.get(
            id=assignment_id, vehicle__owner=request.user, is_active=True
        )
    except OperatorAssignment.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Assignment not found or you do not have permission to modify it",
            },
            status=404,
        )

    if request.method == "POST":
        confirmation = request.POST.get("confirmation")
        reason = request.POST.get("reason", "").strip()

        if confirmation == "confirm":
            assignment.is_active = False
            assignment.deactivated_at = timezone.now()
            assignment.deactivated_by = request.user
            assignment.deactivation_reason = reason
            assignment.save()

            logger.info(
                f"Operator assignment {assignment_id} deactivated by {request.user.username}. "
                f"Operator: {assignment.operator.username}, Vehicle: {assignment.vehicle.plate_number}"
            )

            # Send admin notification
            notify_admins(
                "operator_assignment_removed",
                f"Operator {assignment.operator.username} removed from vehicle {assignment.vehicle.plate_number} by {request.user.username}",
                {
                    "assignment_id": assignment.id,
                    "vehicle_id": assignment.vehicle.id,
                    "operator_id": assignment.operator.id,
                    "reason": reason,
                },
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Operator {assignment.operator.get_full_name() or assignment.operator.username} "
                    f"has been removed from vehicle {assignment.vehicle.plate_number}",
                }
            )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Confirmation required to remove operator assignment",
                },
                status=400,
            )

    # GET request - show confirmation form
    context = {
        "assignment": assignment,
        "vehicle": assignment.vehicle,
        "operator": assignment.operator,
    }

    return render(request, "profiles/deactivate_operator.html", context)


@login_required
def get_vehicle_operators(request, vehicle_id):
    """Get all operators for a specific vehicle via AJAX"""
    from .models import VehicleOwnership

    try:
        vehicle = VehicleOwnership.objects.get(id=vehicle_id, owner=request.user)
    except VehicleOwnership.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Vehicle not found"}, status=404
        )

    # Get active assignments
    active_assignments = OperatorAssignment.objects.filter(
        vehicle=vehicle, is_active=True
    ).select_related("operator", "assigned_by")

    operators_data = []
    for assignment in active_assignments:
        operators_data.append(
            {
                "assignment_id": assignment.id,
                "operator_username": assignment.operator.username,
                "operator_name": assignment.operator.get_full_name()
                or assignment.operator.username,
                "operator_email": assignment.operator.email,
                "assigned_at": assignment.assigned_at.strftime("%Y-%m-%d %H:%M"),
                "assigned_by": assignment.assigned_by.get_full_name()
                or assignment.assigned_by.username,
                "is_identity_verified": assignment.operator.profile.is_identity_verified,
            }
        )

    return JsonResponse(
        {
            "success": True,
            "operators": operators_data,
            "vehicle": {
                "id": vehicle.id,
                "plate_number": vehicle.plate_number,
                "display_name": str(vehicle),
            },
        }
    )


@login_required
def search_operators(request):
    """Search for potential operators by username or email"""
    query = request.GET.get("q", "").strip()

    if not query or len(query) < 2:
        return JsonResponse({"operators": []})

    # Search by username or email
    operators = (
        User.objects.filter(
            Q(username__icontains=query) | Q(email__icontains=query),
            is_active=True,
            profile__is_identity_verified=True,
        )
        .exclude(id=request.user.id)  # Exclude current user
        .select_related("profile")[:10]
    )

    results = []
    for operator in operators:
        # Check if operator already has an active assignment
        has_active_assignment = OperatorAssignment.objects.filter(
            operator=operator, is_active=True
        ).exists()

        results.append(
            {
                "username": operator.username,
                "email": operator.email,
                "full_name": operator.get_full_name() or "",
                "has_active_assignment": has_active_assignment,
                "profile_complete": bool(operator.profile.is_identity_verified),
            }
        )

    logger.debug(
        f"Operator search by {request.user.username} for query '{query}': "
        f"{len(results)} results"
    )

    return JsonResponse({"operators": results})


@login_required
def vehicle_operator_history(request, vehicle_id):
    """Get assignment history for a specific vehicle"""
    from .models import VehicleOwnership

    try:
        vehicle = VehicleOwnership.objects.get(id=vehicle_id, owner=request.user)
    except VehicleOwnership.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Vehicle not found"}, status=404
        )

    # Get all assignments (active and inactive) ordered by most recent first
    all_assignments = (
        OperatorAssignment.objects.filter(vehicle=vehicle)
        .select_related("operator", "assigned_by", "deactivated_by")
        .order_by("-assigned_at")
    )

    history_data = []
    for assignment in all_assignments:
        assignment_data = {
            "assignment_id": assignment.id,
            "operator_username": assignment.operator.username,
            "operator_name": assignment.operator.get_full_name()
            or assignment.operator.username,
            "assigned_at": assignment.assigned_at.strftime("%Y-%m-%d %H:%M"),
            "assigned_by": assignment.assigned_by.get_full_name()
            or assignment.assigned_by.username,
            "is_active": assignment.is_active,
            "deactivated_at": None,
            "deactivated_by": None,
            "deactivation_reason": assignment.deactivation_reason or "",
        }

        if not assignment.is_active and assignment.deactivated_at:
            assignment_data.update(
                {
                    "deactivated_at": assignment.deactivated_at.strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    "deactivated_by": (
                        (
                            assignment.deactivated_by.get_full_name()
                            or assignment.deactivated_by.username
                        )
                        if assignment.deactivated_by
                        else "System"
                    ),
                }
            )

        history_data.append(assignment_data)

    return JsonResponse(
        {
            "success": True,
            "history": history_data,
            "vehicle": {
                "id": vehicle.id,
                "plate_number": vehicle.plate_number,
                "display_name": str(vehicle),
            },
        }
    )


@login_required
def get_operator_vehicles(request):
    """Get vehicles assigned to current operator"""
    from .models import OperatorAssignment, Document

    # Get all active assignments for this operator
    active_assignments = OperatorAssignment.objects.filter(
        operator=request.user, is_active=True
    ).select_related("vehicle", "vehicle__owner")

    vehicles_data = []
    for assignment in active_assignments:
        vehicle = assignment.vehicle

        # Get vehicle documents status
        required_docs = vehicle.get_required_documents()
        docs_status = []
        for doc_type in required_docs:
            docs_status.append(
                {
                    "type": doc_type,
                    "display": dict(Document.DOC_TYPE_CHOICES)[doc_type],
                    "status": vehicle.get_document_status(doc_type),
                }
            )

        vehicles_data.append(
            {
                "assignment_id": assignment.id,
                "vehicle_id": vehicle.id,
                "plate_number": vehicle.plate_number,
                "make": vehicle.make,
                "model": vehicle.model,
                "year": vehicle.year,
                "vehicle_type": vehicle.get_vehicle_type_display(),
                "owner_name": vehicle.owner.get_full_name() or vehicle.owner.username,
                "assigned_at": assignment.assigned_at.strftime("%Y-%m-%d %H:%M"),
                "documents": docs_status,
                "is_fully_documented": vehicle.is_fully_documented(),
            }
        )

    return JsonResponse(
        {"success": True, "vehicles": vehicles_data, "total_count": len(vehicles_data)}
    )


@login_required
def get_operator_assignments(request, operator_id):
    """Get all assignments for a specific operator (admin/owner view)"""
    from django.contrib.auth.models import User
    from .models import OperatorAssignment

    # Ensure requesting user has permission (is either the operator or an admin)
    if request.user.id != operator_id and not request.user.is_staff:
        return JsonResponse(
            {"success": False, "message": "Permission denied"}, status=403
        )

    try:
        operator = User.objects.get(id=operator_id)
    except User.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Operator not found"}, status=404
        )

    # Get active assignments
    active_assignments = OperatorAssignment.objects.filter(
        operator=operator, is_active=True
    ).select_related("vehicle", "vehicle__owner", "assigned_by")

    # Get inactive assignments (history)
    inactive_assignments = (
        OperatorAssignment.objects.filter(operator=operator, is_active=False)
        .select_related("vehicle", "vehicle__owner", "assigned_by", "deactivated_by")
        .order_by("-deactivated_at")[:10]
    )

    # Format active assignments
    active_data = []
    for assignment in active_assignments:
        active_data.append(
            {
                "assignment_id": assignment.id,
                "vehicle_id": assignment.vehicle.id,
                "plate_number": assignment.vehicle.plate_number,
                "make": assignment.vehicle.make,
                "model": assignment.vehicle.model,
                "year": assignment.vehicle.year,
                "vehicle_type": assignment.vehicle.get_vehicle_type_display(),
                "owner_name": assignment.vehicle.owner.get_full_name()
                or assignment.vehicle.owner.username,
                "assigned_at": assignment.assigned_at.strftime("%Y-%m-%d %H:%M"),
                "assigned_by": assignment.assigned_by.get_full_name()
                or assignment.assigned_by.username,
            }
        )

    # Format inactive assignments
    history_data = []
    for assignment in inactive_assignments:
        history_data.append(
            {
                "assignment_id": assignment.id,
                "vehicle_id": assignment.vehicle.id,
                "plate_number": assignment.vehicle.plate_number,
                "make": assignment.vehicle.make,
                "model": assignment.vehicle.model,
                "vehicle_type": assignment.vehicle.get_vehicle_type_display(),
                "owner_name": assignment.vehicle.owner.get_full_name()
                or assignment.vehicle.owner.username,
                "assigned_at": assignment.assigned_at.strftime("%Y-%m-%d %H:%M"),
                "assigned_by": assignment.assigned_by.get_full_name()
                or assignment.assigned_by.username,
                "deactivated_at": (
                    assignment.deactivated_at.strftime("%Y-%m-%d %H:%M")
                    if assignment.deactivated_at
                    else None
                ),
                "deactivated_by": (
                    (
                        assignment.deactivated_by.get_full_name()
                        or assignment.deactivated_by.username
                    )
                    if assignment.deactivated_by
                    else "System"
                ),
                "deactivation_reason": assignment.deactivation_reason or "",
            }
        )

    return JsonResponse(
        {
            "success": True,
            "operator": {
                "id": operator.id,
                "username": operator.username,
                "full_name": operator.get_full_name(),
                "email": operator.email,
            },
            "active_assignments": active_data,
            "assignment_history": history_data,
        }
    )


@login_required
def upload_permit_dashboard(request):
    """Upload permit document via AJAX"""
    from .forms import DocumentForm
    from .models import Document, DocumentReview

    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES, vehicle=None)

        if form.is_valid():
            # Check if document type is appropriate
            doc_type = form.cleaned_data["doc_type"]
            if doc_type != "PERMIT":
                return JsonResponse(
                    {
                        "success": False,
                        "errors": {
                            "doc_type": [
                                "Only permit documents can be uploaded with this form"
                            ]
                        },
                    },
                    status=400,
                )

            # Check if permit document already exists and replace it
            try:
                existing_doc = Document.objects.get(
                    user=request.user, doc_type="PERMIT", vehicle__isnull=True
                )
                # Delete old file and review
                if existing_doc.file:
                    existing_doc.file.delete()
                if hasattr(existing_doc, "review"):
                    existing_doc.review.delete()
                existing_doc.delete()

                logger.info(
                    f"Replaced existing permit document for user {request.user.username}"
                )
            except Document.DoesNotExist:
                pass

            # Save new permit document
            document = form.save(user=request.user, vehicle=None)

            logger.info(f"Transport permit uploaded by {request.user.username}")

            return JsonResponse(
                {
                    "success": True,
                    "message": "Transport permit uploaded successfully! Awaiting review.",
                    "document": {
                        "id": document.id,
                        "doc_type": document.doc_type,
                        "doc_type_display": document.get_doc_type_display(),
                        "status": "PENDING",
                        "uploaded_at": document.uploaded_at.strftime("%Y-%m-%d %H:%M"),
                    },
                }
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)

    return JsonResponse({"success": False, "message": "Invalid request"}, status=405)


@login_required
def get_permit_status(request):
    """Get permit document status for current user"""
    from .models import Document, TransportOwnerBadge

    permit_status = {
        "has_permit": False,
        "status": "MISSING",
        "uploaded_at": None,
        "rejection_reason": None,
        "badge_status": {
            "authorized": False,
            "updated_at": None,
        },
    }

    # Get permit document status
    try:
        permit_doc = Document.objects.get(
            user=request.user, doc_type="PERMIT", vehicle__isnull=True
        )
        permit_status["has_permit"] = True
        permit_status["uploaded_at"] = permit_doc.uploaded_at.strftime("%Y-%m-%d %H:%M")

        if hasattr(permit_doc, "review"):
            permit_status["status"] = permit_doc.review.status
            if permit_doc.review.reason:
                permit_status["rejection_reason"] = permit_doc.review.reason
        else:
            permit_status["status"] = "PENDING"

    except Document.DoesNotExist:
        pass

    # Get transport owner badge status
    try:
        badge = TransportOwnerBadge.objects.get(user=request.user)
        permit_status["badge_status"] = {
            "authorized": badge.authorized,
            "updated_at": (
                badge.updated_at.strftime("%Y-%m-%d %H:%M")
                if badge.updated_at
                else None
            ),
        }
    except TransportOwnerBadge.DoesNotExist:
        pass

    return JsonResponse({"success": True, "permit_status": permit_status})


@login_required
def upload_driver_license(request):
    """Upload driver's license document"""
    from .models import Document, DocumentReview
    from .forms import DocumentForm

    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES, vehicle=None)

        if form.is_valid():
            # Check if document type is appropriate
            doc_type = form.cleaned_data["doc_type"]
            if doc_type != "DRIVER_LICENSE":
                return JsonResponse(
                    {
                        "success": False,
                        "errors": {
                            "doc_type": [
                                "Only driver's license can be uploaded with this form"
                            ]
                        },
                    },
                    status=400,
                )

            # Check if document already exists and replace it
            try:
                existing_doc = Document.objects.get(
                    user=request.user, doc_type="DRIVER_LICENSE", vehicle__isnull=True
                )
                # Delete old file and review
                if existing_doc.file:
                    existing_doc.file.delete()
                if hasattr(existing_doc, "review"):
                    existing_doc.review.delete()
                existing_doc.delete()

                logger.info(
                    f"Replaced existing driver's license document for user {request.user.username}"
                )
            except Document.DoesNotExist:
                pass

            # Save new document
            document = form.save(user=request.user, vehicle=None)

            logger.info(f"Driver's license uploaded by {request.user.username}")

            return JsonResponse(
                {
                    "success": True,
                    "message": "Driver's license uploaded successfully! Awaiting review.",
                    "document": {
                        "id": document.id,
                        "doc_type": document.doc_type,
                        "doc_type_display": document.get_doc_type_display(),
                        "status": "PENDING",
                        "uploaded_at": document.uploaded_at.strftime("%Y-%m-%d %H:%M"),
                    },
                }
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)

    # GET request - render the form
    form = DocumentForm(vehicle=None)
    return render(request, "profiles/upload_driver_license.html", {"form": form})


@login_required
def assign_vehicle_operator_new(request, vehicle_id):
    """Assign an operator to a vehicle using OperatorAssignmentForm"""
    from .models import VehicleOwnership

    try:
        vehicle = VehicleOwnership.objects.get(id=vehicle_id, owner=request.user)
    except VehicleOwnership.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Vehicle not found or you do not have permission to assign operators",
            },
            status=404,
        )

    if request.method == "POST":
        form = OperatorAssignmentForm(request.POST, vehicle=vehicle)

        if form.is_valid():
            try:
                assignment = form.save(assigned_by=request.user)

                logger.info(
                    f"Operator {assignment.operator.username} assigned to vehicle "
                    f"{vehicle.plate_number} by {request.user.username}"
                )

                # Send admin notification
                notify_admins(
                    "operator_assignment_created",
                    f"Operator {assignment.operator.username} assigned to vehicle {vehicle.plate_number} by {request.user.username}",
                    {
                        "assignment_id": assignment.id,
                        "vehicle_id": vehicle.id,
                        "operator_id": assignment.operator.id,
                    },
                )

                return JsonResponse(
                    {
                        "success": True,
                        "message": f"Operator {assignment.operator.get_full_name() or assignment.operator.username} "
                        f"has been assigned to vehicle {vehicle.plate_number}",
                        "assignment": {
                            "id": assignment.id,
                            "operator_username": assignment.operator.username,
                            "operator_name": assignment.operator.get_full_name()
                            or assignment.operator.username,
                            "assigned_at": assignment.assigned_at.strftime(
                                "%Y-%m-%d %H:%M"
                            ),
                            "is_active": assignment.active,
                        },
                    }
                )

            except Exception as e:
                logger.error(
                    f"Error creating operator assignment for vehicle {vehicle_id} "
                    f"by {request.user.username}: {str(e)}"
                )
                return JsonResponse(
                    {
                        "success": False,
                        "message": f"Error creating assignment: {str(e)}",
                    },
                    status=500,
                )
        else:
            # Build consistent error format like other AJAX endpoints
            errors = [
                {"field": field, "message": msg}
                for field, errors_list in form.errors.items()
                for msg in errors_list
            ]
            return JsonResponse({"success": False, "errors": errors}, status=400)

    return JsonResponse(
        {"success": False, "message": "Invalid request method"}, status=405
    )


@login_required
def remove_vehicle_operator_new(request, assignment_id):
    """Remove an operator assignment using the new system"""
    try:
        assignment = OperatorAssignment.objects.get(
            id=assignment_id, vehicle__owner=request.user, active=True
        )
    except OperatorAssignment.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Assignment not found or you do not have permission to modify it",
            },
            status=404,
        )

    if request.method == "POST":
        confirmation = request.POST.get("confirmation")
        reason = request.POST.get("reason", "").strip()

        if confirmation == "confirm":
            assignment.active = False
            assignment.deactivated_at = timezone.now()
            assignment.save()

            logger.info(
                f"Operator assignment {assignment_id} deactivated by {request.user.username}. "
                f"Operator: {assignment.operator.username}, Vehicle: {assignment.vehicle.plate_number}"
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Operator {assignment.operator.get_full_name() or assignment.operator.username} "
                    f"has been removed from vehicle {assignment.vehicle.plate_number}",
                }
            )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Confirmation required to remove operator assignment",
                },
                status=400,
            )

    return JsonResponse(
        {"success": False, "message": "Invalid request method"}, status=405
    )


@login_required
def remove_operator_assignment(request):
    """Remove an operator from a vehicle (owner's view)"""
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Invalid request method"}, status=405
        )

    assignment_id = request.POST.get("assignment_id")
    reason = request.POST.get("reason", "").strip()

    if not assignment_id:
        return JsonResponse(
            {"success": False, "message": "Assignment ID is required"}, status=400
        )

    try:
        assignment = OperatorAssignment.objects.get(
            id=assignment_id, vehicle__owner=request.user, is_active=True
        )
    except OperatorAssignment.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Assignment not found or you do not have permission to modify it",
            },
            status=404,
        )

    # Deactivate the assignment
    assignment.is_active = False
    assignment.deactivated_at = timezone.now()
    assignment.deactivated_by = request.user
    assignment.deactivation_reason = reason
    assignment.save()

    logger.info(
        f"Operator {assignment.operator.username} removed from vehicle "
        f"{assignment.vehicle.plate_number} by {request.user.username}"
    )

    return JsonResponse(
        {
            "success": True,
            "message": f"Operator removed successfully from vehicle {assignment.vehicle.plate_number}",
        }
    )


def signup(request):
    """Alias for register view for compatibility with URLs"""
    return register(request)


def verify_email(request, user_id, token):
    """Alias for confirm_email view for compatibility with URLs"""
    # Convert user_id to base64 string as confirm_email expects uidb64
    uidb64 = urlsafe_base64_encode(force_bytes(user_id))
    return confirm_email(request, uidb64, token)


def resend_verification_email(request):
    """Alias for resend_account_otp for compatibility with URLs"""
    return resend_account_otp(request)


def verification_sent(request):
    """Simple view to show verification email has been sent"""
    return render(request, "profiles/verification_sent.html")
