from django.contrib import admin
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import path
from django.db.models import Q
from django.utils.html import format_html
from .models import (
    Profile,
    IdentityVerification,
    Vehicle,
    VehicleDocument,
    GovernmentPermit,
    OperatorDocument,
    Referral,
    VehicleOwnership,
    Document,
    DocumentReview,
    OperatorAssignment,
    TransportOwnerBadge,
    Portfolio,
    Education,
    Experience,
)


class IdentityVerificationInline(admin.StackedInline):
    model = IdentityVerification
    can_delete = False
    extra = 0
    readonly_fields = (
        "id_card",
        "id_card_rejection_reason",
        "face_photo",
        "face_photo_rejection_reason",
        "proof_of_residence",
        "proof_of_residence_rejection_reason",
    )
    fields = (
        "id_card",
        "id_card_verified",
        "id_card_verified_at",
        "id_card_verified_by",
        "id_card_rejection_reason",
        "face_photo",
        "face_photo_verified",
        "face_photo_verified_at",
        "face_photo_verified_by",
        "face_photo_rejection_reason",
        "proof_of_residence",
        "proof_of_residence_verified",
        "proof_of_residence_verified_at",
        "proof_of_residence_verified_by",
        "proof_of_residence_rejection_reason",
    )


class GovernmentPermitInline(admin.StackedInline):
    model = GovernmentPermit
    can_delete = True
    extra = 0
    readonly_fields = (
        "permit_type",
        "permit_number",
        "issue_date",
        "expiry_date",
        "permit_document",
        "rejection_reason",
    )
    fields = (
        "permit_type",
        "permit_number",
        "issue_date",
        "expiry_date",
        "permit_document",
        "is_verified",
        "verified_at",
        "verified_by",
        "rejection_reason",
    )


class VehicleDocumentInline(admin.StackedInline):
    model = VehicleDocument
    can_delete = False
    extra = 0
    readonly_fields = (
        "drivers_license",
        "drivers_license_rejection_reason",
        "blue_book",
        "blue_book_rejection_reason",
        "inspection_certificate",
        "inspection_certificate_rejection_reason",
        "insurance",
        "insurance_rejection_reason",
    )
    fields = (
        "drivers_license",
        "drivers_license_verified",
        "drivers_license_verified_at",
        "drivers_license_verified_by",
        "drivers_license_rejection_reason",
        "blue_book",
        "blue_book_verified",
        "blue_book_verified_at",
        "blue_book_verified_by",
        "blue_book_rejection_reason",
        "inspection_certificate",
        "inspection_certificate_verified",
        "inspection_certificate_verified_at",
        "inspection_certificate_verified_by",
        "inspection_certificate_rejection_reason",
        "insurance",
        "insurance_verified",
        "insurance_verified_at",
        "insurance_verified_by",
        "insurance_rejection_reason",
    )


class OperatorDocumentInline(admin.StackedInline):
    model = OperatorDocument
    can_delete = True
    extra = 0
    readonly_fields = (
        "user",
        "vehicle",
        "drivers_license",
        "drivers_license_rejection_reason",
    )
    fields = (
        "user",
        "vehicle",
        "drivers_license",
        "drivers_license_verified",
        "drivers_license_verified_at",
        "drivers_license_verified_by",
        "drivers_license_rejection_reason",
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "account_type",
        "average_rating",
        "total_reviews",
        "is_identity_verified",
        "is_vehicle_verified",
        "is_permit_verified",
    )
    readonly_fields = (
        "user",
        "first_name",
        "middle_name",
        "last_name",
        "gender",
        "bio",
        "phone_number",
        "profile_picture",
        "location",
        "title",
        "languages",
        "github_profile",
        "linkedin_profile",
        "skills",
        "hourly_rate",
        "total_projects",
        "success_rate",
        "years_of_experience",
        "preferred_project_size",
        "account_type",
        "average_rating",
        "total_reviews",
        "is_identity_verified",
        "is_vehicle_verified",
        "is_permit_verified",
    )
    inlines = [IdentityVerificationInline, GovernmentPermitInline]
    search_fields = ("user__username", "first_name", "last_name", "title")
    actions = ["verify_selected_documents"]

    def verify_selected_documents(self, request, queryset):
        if queryset.count() == 1:
            profile = queryset.first()
            return redirect("admin:profiles_profile_verify_documents", profile.id)
        self.message_user(
            request,
            "Select exactly one profile for verification.",
            level=messages.ERROR,
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:profile_id>/verify-documents/",
                self.admin_site.admin_view(self.verify_documents),
                name="profiles_profile_verify_documents",
            ),
        ]
        return custom_urls + urls

    def verify_documents(self, request, profile_id):
        profile = get_object_or_404(Profile, id=profile_id)
        identity_verification = getattr(profile, "identity_verification", None)
        vehicles = profile.vehicles.filter(is_active=True).order_by("-id")
        permits = profile.government_permits.filter(is_verified=False).order_by("-id")
        operator_docs = OperatorDocument.objects.filter(
            user=profile.user, drivers_license_verified=False
        ).order_by("-created_at")
        identity_docs = IdentityVerification.objects.filter(
            Q(id_card_verified=False)
            | Q(face_photo_verified=False)
            | Q(proof_of_residence_verified=False),
            profile=profile,
        ).order_by("-id")
        context = {
            "profile": profile,
            "identity_verification": identity_verification,
            "vehicles": vehicles,
            "permits": permits,
            "operator_docs": operator_docs,
            "identity_docs": identity_docs,
        }
        return render(request, "admin/profiles/verify_documents.html", context)


@admin.register(IdentityVerification)
class IdentityVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "id_card_verified",
        "face_photo_verified",
        "proof_of_residence_verified",
    )
    list_filter = (
        "id_card_verified",
        "face_photo_verified",
        "proof_of_residence_verified",
    )
    readonly_fields = (
        "profile",
        "id_card",
        "id_card_rejection_reason",
        "face_photo",
        "face_photo_rejection_reason",
        "proof_of_residence",
        "proof_of_residence_rejection_reason",
    )
    actions = [
        "approve_id_card",
        "reject_id_card",
        "approve_face_photo",
        "reject_face_photo",
        "approve_proof_of_residence",
        "reject_proof_of_residence",
    ]

    def approve_id_card(self, request, queryset):
        for verification in queryset:
            verification.id_card_verified = True
            verification.id_card_verified_at = timezone.now()
            verification.id_card_verified_by = request.user
            verification.id_card_rejection_reason = None
            verification.save()
            verification.profile.save()  # Update is_identity_verified
        self.message_user(request, "Selected ID cards approved.")

    def reject_id_card(self, request, queryset):
        for verification in queryset:
            verification.id_card_verified = False
            verification.id_card_verified_at = None
            verification.id_card_verified_by = None
            verification.id_card_rejection_reason = "Rejected by admin."
            verification.save()
            verification.profile.save()
        self.message_user(request, "Selected ID cards rejected.")

    def approve_face_photo(self, request, queryset):
        for verification in queryset:
            verification.face_photo_verified = True
            verification.face_photo_verified_at = timezone.now()
            verification.face_photo_verified_by = request.user
            verification.face_photo_rejection_reason = None
            verification.save()
            verification.profile.save()
        self.message_user(request, "Selected face photos approved.")

    def reject_face_photo(self, request, queryset):
        for verification in queryset:
            verification.face_photo_verified = False
            verification.face_photo_verified_at = None
            verification.face_photo_verified_by = None
            verification.face_photo_rejection_reason = "Rejected by admin."
            verification.save()
            verification.profile.save()
        self.message_user(request, "Selected face photos rejected.")

    def approve_proof_of_residence(self, request, queryset):
        for verification in queryset:
            verification.proof_of_residence_verified = True
            verification.proof_of_residence_verified_at = timezone.now()
            verification.proof_of_residence_verified_by = request.user
            verification.proof_of_residence_rejection_reason = None
            verification.save()
            verification.profile.save()
        self.message_user(request, "Selected proofs of residence approved.")

    def reject_proof_of_residence(self, request, queryset):
        for verification in queryset:
            verification.proof_of_residence_verified = False
            verification.proof_of_residence_verified_at = None
            verification.proof_of_residence_verified_by = None
            verification.proof_of_residence_rejection_reason = "Rejected by admin."
            verification.save()
            verification.profile.save()
        self.message_user(request, "Selected proofs of residence rejected.")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:iv_id>/verify/<str:field>/",
                self.admin_site.admin_view(self.verify_identity_document),
                name="profiles_identityverification_verify",
            ),
        ]
        return custom_urls + urls

    def verify_identity_document(self, request, iv_id, field):
        iv = get_object_or_404(IdentityVerification, id=iv_id)
        if request.method == "POST":
            action = request.POST.get("action")
            rejection_reason = request.POST.get("rejection_reason", None)
            try:
                if action == "approve":
                    setattr(iv, f"{field}_verified", True)
                    setattr(iv, f"{field}_verified_by", request.user)
                    setattr(iv, f"{field}_verified_at", timezone.now())
                    setattr(iv, f"{field}_rejection_reason", None)
                    messages.success(
                        request, f'{field.replace("_", " ").title()} verified.'
                    )
                elif action == "reject":
                    setattr(iv, f"{field}_verified", False)
                    setattr(iv, f"{field}_verified_by", None)
                    setattr(iv, f"{field}_verified_at", None)
                    setattr(iv, f"{field}_rejection_reason", rejection_reason)
                    messages.success(
                        request, f'{field.replace("_", " ").title()} rejected.'
                    )
                iv.save()
                iv.profile.save()  # Update is_identity_verified
                return redirect("admin:profiles_identityverification_changelist")
            except Exception as e:
                messages.error(request, f"Error updating verification: {str(e)}")
                return redirect("admin:profiles_identityverification_changelist")
        context = {
            "iv": iv,
            "field": field,
            "document_url": getattr(iv, field).url if getattr(iv, field) else None,
        }
        return render(
            request, "admin/profiles/admin_verify_identity_document.html", context
        )


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "make",
        "model",
        "year",
        "license_plate",
        "vehicle_type",
        "is_verified",
        "last_inspection_date",
        "next_inspection_date",
    )
    list_filter = ("is_verified", "vehicle_type")
    readonly_fields = (
        "profile",
        "make",
        "model",
        "year",
        "license_plate",
        "vehicle_type",
        "is_active",
        "is_verified",
        "last_inspection_date",
        "next_inspection_date",
    )
    inlines = [VehicleDocumentInline, OperatorDocumentInline]
    search_fields = ("profile__user__username", "make", "model", "license_plate")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:vehicle_id>/verify/<str:field>/",
                self.admin_site.admin_view(self.verify_vehicle),
                name="profiles_vehicle_verify",
            ),
        ]
        return custom_urls + urls

    def verify_vehicle(self, request, vehicle_id, field):
        vehicle = get_object_or_404(Vehicle, id=vehicle_id)
        document = vehicle.documents.first()
        if not document:
            messages.error(request, "No documents found for this vehicle.")
            return redirect("admin:profiles_vehicle_changelist")

        if request.method == "POST":
            action = request.POST.get("action")
            rejection_reason = request.POST.get("rejection_reason", "")

            if field not in [
                "drivers_license",
                "blue_book",
                "inspection_certificate",
                "insurance",
            ]:
                messages.error(request, "Invalid document field.")
                return redirect("admin:profiles_vehicle_changelist")

            try:
                if action == "approve":
                    setattr(document, f"{field}_verified", True)
                    setattr(document, f"{field}_verified_by", request.user)
                    setattr(document, f"{field}_verified_at", timezone.now())
                    setattr(document, f"{field}_rejection_reason", None)
                elif action == "reject":
                    setattr(document, f"{field}_verified", False)
                    setattr(document, f"{field}_verified_by", None)
                    setattr(document, f"{field}_verified_at", None)
                    setattr(document, f"{field}_rejection_reason", rejection_reason)
                document.save()

                vehicle.is_verified = all(
                    [
                        document.drivers_license_verified,
                        document.blue_book_verified,
                        document.inspection_certificate_verified,
                        document.insurance_verified,
                    ]
                )
                vehicle.save()

                if vehicle.is_verified:
                    profile = vehicle.profile
                    profile.account_type = "TRANSPORT"
                    profile.save()
                    for operator in vehicle.operators.all():
                        if OperatorDocument.objects.filter(
                            user=operator,
                            vehicle=vehicle,
                            drivers_license_verified=True,
                        ).exists():
                            operator.profile.account_type = "TRANSPORT"
                            operator.profile.save()
                    messages.success(
                        request,
                        f"User {profile.user.username} and verified operators registered as Transport Service Provider.",
                    )

                messages.success(
                    request, f'{field.replace("_", " ").title()} verification updated.'
                )
                return redirect("admin:profiles_vehicle_changelist")
            except Exception as e:
                messages.error(request, f"Error updating verification: {str(e)}")
                return redirect("admin:profiles_vehicle_changelist")

        return render(
            request,
            "admin/profiles/admin_verify_vehicle_document.html",
            {
                "vehicle": vehicle,
                "document": document,
                "field": field,
                "label": dict(
                    VehicleDocument._meta.get_field(field).choices
                    or [(field, field.replace("_", " ").title())]
                )[field],
            },
        )


@admin.register(VehicleDocument)
class VehicleDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "vehicle",
        "drivers_license_verified",
        "blue_book_verified",
        "inspection_certificate_verified",
        "insurance_verified",
    )
    list_filter = (
        "drivers_license_verified",
        "blue_book_verified",
        "inspection_certificate_verified",
        "insurance_verified",
    )
    readonly_fields = (
        "vehicle",
        "drivers_license",
        "blue_book",
        "inspection_certificate",
        "insurance",
    )
    actions = [
        "approve_drivers_license",
        "reject_drivers_license",
        "approve_blue_book",
        "reject_blue_book",
        "approve_inspection_certificate",
        "reject_inspection_certificate",
        "approve_insurance",
        "reject_insurance",
    ]

    def approve_drivers_license(self, request, queryset):
        for document in queryset:
            document.drivers_license_verified = True
            document.drivers_license_verified_at = timezone.now()
            document.drivers_license_verified_by = request.user
            document.drivers_license_rejection_reason = None
            document.save()
            document.vehicle.save()  # Update is_verified and account_type
        self.message_user(request, "Selected driver’s licenses approved.")

    def reject_drivers_license(self, request, queryset):
        for document in queryset:
            document.drivers_license_verified = False
            document.drivers_license_verified_at = None
            document.drivers_license_verified_by = None
            document.drivers_license_rejection_reason = "Rejected by admin."
            document.save()
            document.vehicle.save()
        self.message_user(request, "Selected driver’s licenses rejected.")

    def approve_blue_book(self, request, queryset):
        for document in queryset:
            document.blue_book_verified = True
            document.blue_book_verified_at = timezone.now()
            document.blue_book_verified_by = request.user
            document.blue_book_rejection_reason = None
            document.save()
            document.vehicle.save()
        self.message_user(request, "Selected blue books approved.")

    def reject_blue_book(self, request, queryset):
        for document in queryset:
            document.blue_book_verified = False
            document.blue_book_verified_at = None
            document.blue_book_verified_by = None
            document.blue_book_rejection_reason = "Rejected by admin."
            document.save()
            document.vehicle.save()
        self.message_user(request, "Selected blue books rejected.")

    def approve_inspection_certificate(self, request, queryset):
        for document in queryset:
            document.inspection_certificate_verified = True
            document.inspection_certificate_verified_at = timezone.now()
            document.inspection_certificate_verified_by = request.user
            document.inspection_certificate_rejection_reason = None
            document.save()
            document.vehicle.save()
        self.message_user(request, "Selected inspection certificates approved.")

    def reject_inspection_certificate(self, request, queryset):
        for document in queryset:
            document.inspection_certificate_verified = False
            document.inspection_certificate_verified_at = None
            document.inspection_certificate_verified_by = None
            document.inspection_certificate_rejection_reason = "Rejected by admin."
            document.save()
            document.vehicle.save()
        self.message_user(request, "Selected inspection certificates rejected.")

    def approve_insurance(self, request, queryset):
        for document in queryset:
            document.insurance_verified = True
            document.insurance_verified_at = timezone.now()
            document.insurance_verified_by = request.user
            document.insurance_rejection_reason = None
            document.save()
            document.vehicle.save()
        self.message_user(request, "Selected insurance documents approved.")

    def reject_insurance(self, request, queryset):
        for document in queryset:
            document.insurance_verified = False
            document.insurance_verified_at = None
            document.insurance_verified_by = None
            document.insurance_rejection_reason = "Rejected by admin."
            document.save()
            document.vehicle.save()
        self.message_user(request, "Selected insurance documents rejected.")


@admin.register(GovernmentPermit)
class GovernmentPermitAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "permit_type",
        "permit_number",
        "issue_date",
        "expiry_date",
        "is_verified",
        "verified_at",
        "verified_by",
    )
    list_filter = ("permit_type", "is_verified")
    readonly_fields = (
        "profile",
        "permit_type",
        "permit_number",
        "issue_date",
        "expiry_date",
        "permit_document",
    )
    actions = ["approve_permit", "reject_permit"]

    def approve_permit(self, request, queryset):
        for permit in queryset:
            permit.is_verified = True
            permit.verified_at = timezone.now()
            permit.verified_by = request.user
            permit.rejection_reason = None
            permit.save()
            permit.profile.save()  # Update is_permit_verified
        self.message_user(request, "Selected permits approved.")

    def reject_permit(self, request, queryset):
        for permit in queryset:
            permit.is_verified = False
            permit.verified_at = None
            permit.verified_by = None
            permit.rejection_reason = "Rejected by admin."
            permit.save()
            permit.profile.save()
        self.message_user(request, "Selected permits rejected.")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:permit_id>/verify/",
                self.admin_site.admin_view(self.verify_permit_document),
                name="profiles_governmentpermit_verify",
            ),
        ]
        return custom_urls + urls

    def verify_permit_document(self, request, permit_id):
        permit = get_object_or_404(GovernmentPermit, id=permit_id)

        if request.method == "POST":
            action = request.POST.get("action")
            rejection_reason = request.POST.get("rejection_reason", "")

            try:
                if action == "approve":
                    permit.is_verified = True
                    permit.verified_by = request.user
                    permit.verified_at = timezone.now()
                    permit.rejection_reason = None
                elif action == "reject":
                    permit.is_verified = False
                    permit.verified_by = None
                    permit.verified_at = None
                    permit.rejection_reason = rejection_reason
                permit.save()
                permit.profile.save()  # Update is_permit_verified
                messages.success(request, "Permit verification updated.")
                return redirect("admin:profiles_governmentpermit_changelist")
            except Exception as e:
                messages.error(request, f"Error updating permit verification: {str(e)}")
                return redirect("admin:profiles_governmentpermit_changelist")

        return render(
            request,
            "admin/profiles/admin_verify_permit_document.html",
            {"permit": permit, "label": "Transport Permit"},
        )


@admin.register(OperatorDocument)
class OperatorDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "vehicle",
        "drivers_license_verified",
        "drivers_license_verified_at",
    )
    list_filter = ("drivers_license_verified",)
    readonly_fields = ("user", "vehicle", "drivers_license")
    actions = ["approve_operator_license", "reject_operator_license"]

    def approve_operator_license(self, request, queryset):
        for operator_doc in queryset:
            operator_doc.drivers_license_verified = True
            operator_doc.drivers_license_verified_at = timezone.now()
            operator_doc.drivers_license_verified_by = request.user
            operator_doc.drivers_license_rejection_reason = None
            operator_doc.save()
            if operator_doc.vehicle.is_verified:
                operator_doc.user.profile.account_type = "TRANSPORT"
                operator_doc.user.profile.save()
            operator_doc.vehicle.save()  # Update vehicle.is_verified
        self.message_user(request, "Selected operator driver’s licenses approved.")

    def reject_operator_license(self, request, queryset):
        for operator_doc in queryset:
            operator_doc.drivers_license_verified = False
            operator_doc.drivers_license_verified_at = None
            operator_doc.drivers_license_verified_by = None
            operator_doc.drivers_license_rejection_reason = "Rejected by admin."
            operator_doc.save()
            if (
                not operator_doc.user.operated_vehicles.filter(
                    is_verified=True, operator_documents__drivers_license_verified=True
                ).exists()
                and not operator_doc.user.profile.vehicles.filter(
                    is_verified=True
                ).exists()
            ):
                operator_doc.user.profile.account_type = "REGULAR"
                operator_doc.user.profile.save()
            operator_doc.vehicle.save()
        self.message_user(request, "Selected operator driver’s licenses rejected.")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:doc_id>/verify/",
                self.admin_site.admin_view(self.verify_operator_document),
                name="profiles_operatordocument_verify",
            ),
        ]
        return custom_urls + urls

    def verify_operator_document(self, request, doc_id):
        operator_doc = get_object_or_404(OperatorDocument, id=doc_id)
        if request.method == "POST":
            action = request.POST.get("action")
            rejection_reason = request.POST.get("rejection_reason", "")

            try:
                if action == "approve":
                    operator_doc.drivers_license_verified = True
                    operator_doc.drivers_license_verified_by = request.user
                    operator_doc.drivers_license_verified_at = timezone.now()
                    operator_doc.drivers_license_rejection_reason = None
                    if operator_doc.vehicle.is_verified:
                        operator_doc.user.profile.account_type = "TRANSPORT"
                        operator_doc.user.profile.save()
                elif action == "reject":
                    operator_doc.drivers_license_verified = False
                    operator_doc.drivers_license_verified_by = None
                    operator_doc.drivers_license_verified_at = None
                    operator_doc.drivers_license_rejection_reason = rejection_reason
                    if (
                        not operator_doc.user.operated_vehicles.filter(
                            is_verified=True,
                            operator_documents__drivers_license_verified=True,
                        ).exists()
                        and not operator_doc.user.profile.vehicles.filter(
                            is_verified=True
                        ).exists()
                    ):
                        operator_doc.user.profile.account_type = "REGULAR"
                        operator_doc.user.profile.save()
                operator_doc.save()
                operator_doc.vehicle.save()
                messages.success(
                    request, "Operator driver’s license verification updated."
                )
                return redirect("admin:profiles_operatordocument_changelist")
            except Exception as e:
                messages.error(request, f"Error updating verification: {str(e)}")
                return redirect("admin:profiles_operatordocument_changelist")

        return render(
            request,
            "admin/profiles/admin_verify_operator_document.html",
            {"operator_doc": operator_doc, "label": "Operator Driver's License"},
        )


# New Vehicle Workflow Admin Classes
class DocumentReviewInline(admin.StackedInline):
    model = DocumentReview
    can_delete = False
    extra = 0
    readonly_fields = (
        "document",
        "created_at",
        "reviewed_at",
    )
    fields = (
        "document",
        "status",
        "reason",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    )


@admin.register(VehicleOwnership)
class VehicleOwnershipAdmin(admin.ModelAdmin):
    list_display = (
        "plate_number",
        "owner",
        "get_vehicle_display",
        "is_fully_documented",
        "created_at",
    )
    list_filter = (
        "vehicle_type",
        "created_at",
    )
    search_fields = (
        "plate_number",
        "owner__username",
        "owner__first_name",
        "owner__last_name",
        "make",
        "model",
    )
    readonly_fields = (
        "owner",
        "created_at",
        "is_fully_documented",
        "get_document_summary",
    )
    date_hierarchy = "created_at"
    actions = ["export_vehicle_data"]

    def get_vehicle_display(self, obj):
        """Display vehicle information"""
        if obj.make:
            return f"{obj.year} {obj.make} {obj.model}"
        return "Vehicle"

    get_vehicle_display.short_description = "Vehicle"

    def get_document_summary(self, obj):
        """Show document status summary"""
        required_docs = obj.get_required_documents()
        status_list = []

        for doc_type in required_docs:
            status = obj.get_document_status(doc_type)
            doc_name = dict(Document.DOC_TYPE_CHOICES).get(doc_type, doc_type)
            status_list.append(f"{doc_name}: {status}")

        return "\n".join(status_list)

    get_document_summary.short_description = "Document Status"

    def export_vehicle_data(self, request, queryset):
        """Export vehicle data to CSV"""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="vehicle_data.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Plate Number",
                "Owner Username",
                "Owner Email",
                "Owner Full Name",
                "Make",
                "Model",
                "Year",
                "Vehicle Type",
                "Fully Documented",
                "Created Date",
            ]
        )

        for vehicle in queryset:
            writer.writerow(
                [
                    vehicle.plate_number,
                    vehicle.owner.username,
                    vehicle.owner.email,
                    vehicle.owner.get_full_name(),
                    vehicle.make or "",
                    vehicle.model or "",
                    vehicle.year or "",
                    vehicle.get_vehicle_type_display() if vehicle.vehicle_type else "",
                    "Yes" if vehicle.is_fully_documented() else "No",
                    vehicle.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                ]
            )

        return response

    export_vehicle_data.short_description = "Export selected vehicles to CSV"


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "get_document_display",
        "user",
        "vehicle",
        "doc_type",
        "get_review_status",
        "uploaded_at",
    )
    list_filter = (
        "doc_type",
        "uploaded_at",
        "review__status",
    )
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "vehicle__plate_number",
    )
    readonly_fields = (
        "user",
        "vehicle",
        "doc_type",
        "get_file_link",
        "uploaded_at",
        "get_file_info",
    )
    date_hierarchy = "uploaded_at"
    inlines = [DocumentReviewInline]
    actions = [
        "approve_documents",
        "reject_documents",
        "reset_to_pending",
        "export_document_data",
    ]

    def get_document_display(self, obj):
        """Display document information"""
        vehicle_info = f" for {obj.vehicle.plate_number}" if obj.vehicle else ""
        return f"{obj.get_doc_type_display()}{vehicle_info}"

    get_document_display.short_description = "Document"

    def get_review_status(self, obj):
        """Display review status with color coding"""
        try:
            status = obj.review.status
            colors = {
                "PENDING": "#f59e0b",
                "APPROVED": "#10b981",
                "REJECTED": "#ef4444",
            }
            color = colors.get(status, "#6b7280")
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                obj.review.get_status_display(),
            )
        except DocumentReview.DoesNotExist:
            return format_html('<span style="color: #6b7280;">No Review</span>')

    get_review_status.short_description = "Status"

    def get_file_link(self, obj):
        """Display clickable link to view document file"""
        if obj.file:
            file_name = (
                obj.file.name.split("/")[-1]
                if "/" in obj.file.name
                else obj.file.name.split("\\")[-1]
            )
            return format_html(
                '<a href="{}" target="_blank" style="color: #2563eb; text-decoration: underline;">📄 View Document: {}</a>',
                obj.file.url,
                file_name,
            )
        return "No file uploaded"

    get_file_link.short_description = "Document File"

    def get_file_info(self, obj):
        """Display file information"""
        if obj.file:
            try:
                size_mb = obj.file.size / (1024 * 1024)
                return f"Size: {size_mb:.2f} MB\nName: {obj.file.name.split('/')[-1]}"
            except:
                return "File exists"
        return "No file"

    get_file_info.short_description = "File Info"

    def approve_documents(self, request, queryset):
        """Bulk approve documents"""
        count = 0
        for document in queryset:
            review, created = DocumentReview.objects.get_or_create(
                document=document,
                defaults={"status": "APPROVED", "reviewed_by": request.user},
            )
            if not created:
                review.status = "APPROVED"
                review.reviewed_by = request.user
                review.reason = ""
                review.save()
            count += 1

        self.message_user(request, f"{count} document(s) approved successfully.")

    approve_documents.short_description = "Approve selected documents"

    def reject_documents(self, request, queryset):
        """Bulk reject documents (requires reason in separate view)"""
        # For now, just mark as rejected with generic reason
        # In a full implementation, you'd redirect to a form for reasons
        count = 0
        for document in queryset:
            review, created = DocumentReview.objects.get_or_create(
                document=document,
                defaults={
                    "status": "REJECTED",
                    "reviewed_by": request.user,
                    "reason": "Rejected by admin action",
                },
            )
            if not created:
                review.status = "REJECTED"
                review.reviewed_by = request.user
                review.reason = "Rejected by admin action"
                review.save()
            count += 1

        self.message_user(
            request, f"{count} document(s) rejected. Users will be notified."
        )

    reject_documents.short_description = "Reject selected documents"

    def reset_to_pending(self, request, queryset):
        """Reset documents to pending status"""
        count = 0
        for document in queryset:
            review, created = DocumentReview.objects.get_or_create(
                document=document, defaults={"status": "PENDING"}
            )
            if not created:
                review.status = "PENDING"
                review.reviewed_by = None
                review.reviewed_at = None
                review.reason = ""
                review.save()
            count += 1

        self.message_user(request, f"{count} document(s) reset to pending status.")

    reset_to_pending.short_description = "Reset to pending status"

    def export_document_data(self, request, queryset):
        """Export document data to CSV"""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="document_data.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Document Type",
                "User Username",
                "User Email",
                "Vehicle Plate",
                "Review Status",
                "Reviewed By",
                "Upload Date",
                "Review Date",
                "Rejection Reason",
            ]
        )

        for document in queryset:
            review = getattr(document, "review", None)
            writer.writerow(
                [
                    document.get_doc_type_display(),
                    document.user.username,
                    document.user.email,
                    document.vehicle.plate_number if document.vehicle else "",
                    review.get_status_display() if review else "No Review",
                    (
                        review.reviewed_by.username
                        if review and review.reviewed_by
                        else ""
                    ),
                    document.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),
                    (
                        review.reviewed_at.strftime("%Y-%m-%d %H:%M:%S")
                        if review and review.reviewed_at
                        else ""
                    ),
                    review.reason if review else "",
                ]
            )

        return response

    export_document_data.short_description = "Export selected documents to CSV"


@admin.register(DocumentReview)
class DocumentReviewAdmin(admin.ModelAdmin):
    list_display = (
        "get_document_display",
        "status",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    )
    list_filter = (
        "status",
        "reviewed_at",
        "created_at",
        "reviewed_by",
        "document__doc_type",
    )
    search_fields = (
        "document__user__username",
        "document__user__first_name",
        "document__user__last_name",
        "document__vehicle__plate_number",
        "reason",
    )
    readonly_fields = (
        "document",
        "created_at",
        "reviewed_at",
        "get_document_file",
    )
    date_hierarchy = "created_at"
    actions = [
        "bulk_approve",
        "bulk_reject",
        "bulk_reset_pending",
    ]

    def get_document_display(self, obj):
        """Display document information"""
        vehicle_info = (
            f" for {obj.document.vehicle.plate_number}" if obj.document.vehicle else ""
        )
        return f"{obj.document.get_doc_type_display()}{vehicle_info} - {obj.document.user.username}"

    get_document_display.short_description = "Document"

    def get_document_file(self, obj):
        """Display link to document file"""
        if obj.document.file:
            return format_html(
                '<a href="{}" target="_blank">View Document</a>', obj.document.file.url
            )
        return "No file"

    get_document_file.short_description = "Document File"

    def bulk_approve(self, request, queryset):
        """Bulk approve document reviews"""
        count = queryset.update(
            status="APPROVED",
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
            reason="",
        )
        self.message_user(request, f"{count} document review(s) approved successfully.")

    bulk_approve.short_description = "Approve selected reviews"

    def bulk_reject(self, request, queryset):
        """Bulk reject document reviews"""
        count = queryset.update(
            status="REJECTED",
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
            reason="Rejected by admin bulk action",
        )
        self.message_user(
            request, f"{count} document review(s) rejected. Users will be notified."
        )

    bulk_reject.short_description = "Reject selected reviews"

    def bulk_reset_pending(self, request, queryset):
        """Reset reviews to pending"""
        count = queryset.update(
            status="PENDING", reviewed_by=None, reviewed_at=None, reason=""
        )
        self.message_user(request, f"{count} document review(s) reset to pending.")

    bulk_reset_pending.short_description = "Reset to pending status"


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "code",
        "referred_by",
        "total_referrals",
        "created_at",
    )
    list_filter = (
        "referred_by",
        "created_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "code",
        "referred_by__username",
        "referred_by__email",
    )
    readonly_fields = (
        "user",
        "code",
        "referred_by",
        "created_at",
        "total_referrals",
    )
    date_hierarchy = "created_at"
    actions = ["export_referral_data"]

    def total_referrals(self, obj):
        """Display total number of referrals made by this user"""
        return obj.total_referrals

    total_referrals.short_description = "Total Referrals"

    def export_referral_data(self, request, queryset):
        """Export referral data to CSV"""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="referral_data.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Username",
                "Email",
                "Full Name",
                "Referral Code",
                "Referred By Username",
                "Referred By Email",
                "Total Referrals",
                "Created Date",
            ]
        )

        for referral in queryset:
            writer.writerow(
                [
                    referral.user.username,
                    referral.user.email,
                    referral.user.get_full_name(),
                    referral.code,
                    referral.referred_by.username if referral.referred_by else "",
                    referral.referred_by.email if referral.referred_by else "",
                    referral.total_referrals,
                    referral.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                ]
            )

        return response

    export_referral_data.short_description = "Export selected referrals to CSV"


@admin.register(OperatorAssignment)
class OperatorAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "get_assignment_display",
        "vehicle",
        "operator",
        "assigned_by",
        "get_active_status",
        "assigned_at",
        "deactivated_at",
    )
    list_filter = (
        "active",
        "assigned_at",
        "deactivated_at",
        "vehicle__vehicle_type",
        "assigned_by",
    )
    search_fields = (
        "vehicle__plate_number",
        "operator__username",
        "operator__first_name",
        "operator__last_name",
        "operator__email",
        "assigned_by__username",
    )
    readonly_fields = (
        "vehicle",
        "operator",
        "assigned_by",
        "assigned_at",
        "deactivated_at",
        "get_assignment_duration",
        "get_operator_info",
        "get_vehicle_info",
    )
    date_hierarchy = "assigned_at"
    actions = [
        "deactivate_assignments",
        "reactivate_assignments",
        "export_assignment_data",
    ]

    fieldsets = (
        (
            "Assignment Information",
            {
                "fields": (
                    "vehicle",
                    "operator",
                    "assigned_by",
                    "active",
                )
            },
        ),
        (
            "Dates",
            {
                "fields": (
                    "assigned_at",
                    "deactivated_at",
                    "get_assignment_duration",
                )
            },
        ),
        (
            "Additional Information",
            {
                "fields": (
                    "get_operator_info",
                    "get_vehicle_info",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_assignment_display(self, obj):
        """Display assignment information"""
        return f"{obj.operator.username} → {obj.vehicle.plate_number}"

    get_assignment_display.short_description = "Assignment"

    def get_active_status(self, obj):
        """Display active status with color coding"""
        if obj.active:
            return format_html(
                '<span style="color: #10b981; font-weight: bold;">✓ Active</span>'
            )
        else:
            return format_html(
                '<span style="color: #ef4444; font-weight: bold;">✗ Inactive</span>'
            )

    get_active_status.short_description = "Status"

    def get_assignment_duration(self, obj):
        """Display assignment duration"""
        if obj.active:
            duration = timezone.now() - obj.assigned_at
        elif obj.deactivated_at:
            duration = obj.deactivated_at - obj.assigned_at
        else:
            return "Unknown"

        days = duration.days
        hours = duration.seconds // 3600

        if days > 0:
            return f"{days} days, {hours} hours"
        else:
            return f"{hours} hours"

    get_assignment_duration.short_description = "Duration"

    def get_operator_info(self, obj):
        """Display operator information"""
        operator = obj.operator
        info_lines = [
            f"Full Name: {operator.get_full_name() or 'Not provided'}",
            f"Email: {operator.email}",
            f"Identity Verified: {'Yes' if operator.profile.is_identity_verified else 'No'}",
            f"Account Type: {operator.profile.get_account_type_display()}",
            f"Transport Owner Tag: {'Yes' if operator.profile.transport_owner_tag else 'No'}",
        ]
        return "\n".join(info_lines)

    get_operator_info.short_description = "Operator Details"

    def get_vehicle_info(self, obj):
        """Display vehicle information"""
        vehicle = obj.vehicle
        info_lines = [
            f"Owner: {vehicle.owner.username} ({vehicle.owner.get_full_name() or 'No name'})",
            f"Vehicle: {vehicle.year or ''} {vehicle.make or ''} {vehicle.model or ''}".strip(),
            f"Type: {vehicle.get_vehicle_type_display() if vehicle.vehicle_type else 'Not specified'}",
            f"Fully Documented: {'Yes' if vehicle.is_fully_documented() else 'No'}",
        ]
        return "\n".join(info_lines)

    get_vehicle_info.short_description = "Vehicle Details"

    def deactivate_assignments(self, request, queryset):
        """Bulk deactivate operator assignments"""
        count = 0
        for assignment in queryset.filter(active=True):
            assignment.active = False
            assignment.deactivated_at = timezone.now()
            assignment.save()
            count += 1

        self.message_user(
            request,
            f"{count} operator assignment(s) deactivated successfully. Operators have been notified.",
        )

    deactivate_assignments.short_description = "Deactivate selected assignments"

    def reactivate_assignments(self, request, queryset):
        """Bulk reactivate operator assignments"""
        count = 0
        errors = []

        for assignment in queryset.filter(active=False):
            # Check if vehicle already has an active operator
            existing_active = (
                OperatorAssignment.objects.filter(
                    vehicle=assignment.vehicle, active=True
                )
                .exclude(pk=assignment.pk)
                .exists()
            )

            if existing_active:
                errors.append(
                    f"Vehicle {assignment.vehicle.plate_number} already has an active operator"
                )
                continue

            assignment.active = True
            assignment.deactivated_at = None
            assignment.save()
            count += 1

        if count > 0:
            self.message_user(
                request, f"{count} operator assignment(s) reactivated successfully."
            )

        if errors:
            for error in errors[:5]:  # Show max 5 errors
                messages.warning(request, error)

    reactivate_assignments.short_description = "Reactivate selected assignments"

    def export_assignment_data(self, request, queryset):
        """Export assignment data to CSV"""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="operator_assignments.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            [
                "Vehicle Plate",
                "Vehicle Owner",
                "Operator Username",
                "Operator Name",
                "Operator Email",
                "Assigned By",
                "Active",
                "Assigned Date",
                "Deactivated Date",
                "Duration (Days)",
                "Operator Identity Verified",
                "Vehicle Fully Documented",
                "Transport Owner Tag",
            ]
        )

        for assignment in queryset:
            if assignment.active:
                duration = (timezone.now() - assignment.assigned_at).days
                deactivated_date = ""
            elif assignment.deactivated_at:
                duration = (assignment.deactivated_at - assignment.assigned_at).days
                deactivated_date = assignment.deactivated_at.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            else:
                duration = ""
                deactivated_date = ""

            writer.writerow(
                [
                    assignment.vehicle.plate_number,
                    assignment.vehicle.owner.username,
                    assignment.operator.username,
                    assignment.operator.get_full_name() or "",
                    assignment.operator.email,
                    assignment.assigned_by.username,
                    "Yes" if assignment.active else "No",
                    assignment.assigned_at.strftime("%Y-%m-%d %H:%M:%S"),
                    deactivated_date,
                    duration,
                    "Yes" if assignment.operator.profile.is_identity_verified else "No",
                    "Yes" if assignment.vehicle.is_fully_documented() else "No",
                    "Yes" if assignment.operator.profile.transport_owner_tag else "No",
                ]
            )

        return response

    export_assignment_data.short_description = "Export selected assignments to CSV"


@admin.register(TransportOwnerBadge)
class TransportOwnerBadgeAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "get_authorized_status",
        "updated_at",
        "get_user_info",
    )
    list_filter = (
        "authorized",
        "updated_at",
    )
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    )
    readonly_fields = (
        "user",
        "updated_at",
        "get_user_info",
        "get_permit_status",
    )
    date_hierarchy = "updated_at"
    actions = [
        "authorize_badges",
        "revoke_authorization",
        "export_badge_data",
    ]

    fieldsets = (
        (
            "Badge Information",
            {
                "fields": (
                    "user",
                    "authorized",
                    "updated_at",
                )
            },
        ),
        (
            "User Details",
            {
                "fields": (
                    "get_user_info",
                    "get_permit_status",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_authorized_status(self, obj):
        """Display authorized status with color coding"""
        if obj.authorized:
            return format_html(
                '<span style="color: #10b981; font-weight: bold;">✓ Authorized Provider</span>'
            )
        else:
            return format_html(
                '<span style="color: #ef4444; font-weight: bold;">✗ Not Authorized</span>'
            )

    get_authorized_status.short_description = "Authorization Status"

    def get_user_info(self, obj):
        """Display user information"""
        user = obj.user
        info_lines = [
            f"Full Name: {user.get_full_name() or 'Not provided'}",
            f"Email: {user.email}",
            f"Account Type: {user.profile.get_account_type_display()}",
            f"Identity Verified: {'Yes' if user.profile.is_identity_verified else 'No'}",
            f"Vehicle Verified: {'Yes' if user.profile.is_vehicle_verified else 'No'}",
            f"Transport Owner Tag: {'Yes' if user.profile.transport_owner_tag else 'No'}",
        ]
        return "\n".join(info_lines)

    get_user_info.short_description = "User Details"

    def get_permit_status(self, obj):
        """Display permit document status"""
        try:
            permit_docs = obj.user.documents.filter(doc_type="PERMIT")
            if not permit_docs.exists():
                return "No permit documents uploaded"

            status_list = []
            for doc in permit_docs:
                try:
                    review_status = (
                        doc.review.get_status_display()
                        if hasattr(doc, "review")
                        else "No Review"
                    )
                    status_list.append(
                        f"Permit uploaded: {doc.uploaded_at.strftime('%Y-%m-%d')} - Status: {review_status}"
                    )
                except:
                    status_list.append(
                        f"Permit uploaded: {doc.uploaded_at.strftime('%Y-%m-%d')} - No review"
                    )

            return "\n".join(status_list)
        except Exception as e:
            return f"Error checking permit status: {str(e)}"

    get_permit_status.short_description = "Permit Document Status"

    def authorize_badges(self, request, queryset):
        """Bulk authorize transport owner badges"""
        count = queryset.update(authorized=True)
        self.message_user(
            request,
            f"{count} user(s) authorized as transport providers. They will be notified.",
        )

    authorize_badges.short_description = (
        "Authorize selected users as transport providers"
    )

    def revoke_authorization(self, request, queryset):
        """Bulk revoke authorization"""
        count = queryset.update(authorized=False)
        self.message_user(
            request,
            f"Authorization revoked for {count} user(s). They will be notified.",
        )

    revoke_authorization.short_description = "Revoke authorization for selected users"

    def export_badge_data(self, request, queryset):
        """Export badge data to CSV"""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="transport_badges.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Username",
                "Email",
                "Full Name",
                "Authorized",
                "Account Type",
                "Identity Verified",
                "Vehicle Verified",
                "Transport Owner Tag",
                "Updated Date",
            ]
        )

        for badge in queryset:
            writer.writerow(
                [
                    badge.user.username,
                    badge.user.email,
                    badge.user.get_full_name() or "",
                    "Yes" if badge.authorized else "No",
                    badge.user.profile.get_account_type_display(),
                    "Yes" if badge.user.profile.is_identity_verified else "No",
                    "Yes" if badge.user.profile.is_vehicle_verified else "No",
                    "Yes" if badge.user.profile.transport_owner_tag else "No",
                    badge.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                ]
            )

        return response

    export_badge_data.short_description = "Export selected badges to CSV"


# Portfolio, Education, Experience Admin Classes
@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "role",
        "completion_date",
        "created_at",
    )
    list_filter = (
        "completion_date",
        "created_at",
    )
    search_fields = (
        "title",
        "user__username",
        "user__first_name",
        "user__last_name",
        "role",
        "description",
        "skills",
    )
    readonly_fields = (
        "user",
        "created_at",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "user",
                    "title",
                    "role",
                    "completion_date",
                )
            },
        ),
        (
            "Details",
            {
                "fields": (
                    "description",
                    "skills",
                    "related_job",
                    "image",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at",),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = (
        "degree",
        "institution",
        "user",
        "field_of_study",
        "start_date",
        "end_date",
        "current",
    )
    list_filter = (
        "current",
        "start_date",
        "end_date",
    )
    search_fields = (
        "institution",
        "degree",
        "field_of_study",
        "user__username",
        "user__first_name",
        "user__last_name",
        "description",
    )
    readonly_fields = ("profile",)
    date_hierarchy = "start_date"
    ordering = ("-start_date",)

    fieldsets = (
        (
            "Education Information",
            {
                "fields": (
                    "profile",
                    "institution",
                    "degree",
                    "field_of_study",
                )
            },
        ),
        (
            "Duration",
            {
                "fields": (
                    "start_date",
                    "end_date",
                    "current",
                )
            },
        ),
        ("Description", {"fields": ("description",)}),
    )

    def user(self, obj):
        """Display the user associated with this education"""
        return obj.profile.user.username

    user.short_description = "User"


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company",
        "user",
        "location",
        "start_date",
        "end_date",
        "current",
    )
    list_filter = (
        "current",
        "start_date",
        "end_date",
        "company",
    )
    search_fields = (
        "title",
        "company",
        "location",
        "user__username",
        "user__first_name",
        "user__last_name",
        "description",
    )
    readonly_fields = ("profile",)
    date_hierarchy = "start_date"
    ordering = ("-start_date",)

    fieldsets = (
        (
            "Experience Information",
            {
                "fields": (
                    "profile",
                    "title",
                    "company",
                    "location",
                )
            },
        ),
        (
            "Duration",
            {
                "fields": (
                    "start_date",
                    "end_date",
                    "current",
                )
            },
        ),
        ("Description", {"fields": ("description",)}),
    )

    def user(self, obj):
        """Display the user associated with this experience"""
        return obj.profile.user.username

    user.short_description = "User"
