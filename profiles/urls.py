from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = "profiles"

urlpatterns = [
    # Authentication URLs
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="profiles/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", views.signup, name="signup"),
    path("register/", views.register, name="register"),
    # Account verification (OTP-based)
    path("verify-account/", views.verify_account, name="verify_account"),
    path("resend-account-otp/", views.resend_account_otp, name="resend_account_otp"),
    path(
        "verify-email/<int:user_id>/<str:token>/",
        views.verify_email,
        name="verify_email",
    ),
    path(
        "resend-verification/",
        views.resend_verification_email,
        name="resend_verification",
    ),
    path("verification-sent/", views.verification_sent, name="verification_sent"),
    # Password Reset (OTP-based)
    path("reset-request/", views.reset_request, name="reset_request"),
    path("reset-verify/", views.reset_verify, name="reset_verify"),
    path("reset-new-password/", views.reset_new_password, name="reset_new_password"),
    path("resend-reset-otp/", views.resend_reset_otp, name="resend_reset_otp"),
    # Traditional Django auth views (fallback)
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="profiles/password_reset.html"
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="profiles/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="profiles/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="profiles/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    # Profile management
    path("profile/", views.profile, name="profile"),
    path("editProfile/", views.editProfile, name="edit_profile"),
    path("public-profile/<str:username>/", views.publicProfile, name="public_profile"),
    # Vehicle management (legacy)
    path("add-vehicle/", views.add_vehicle, name="add_vehicle"),
    path(
        "add-vehicle-operator/<int:vehicle_id>/",
        views.add_vehicle_operator,
        name="add_vehicle_operator",
    ),
    path("edit-vehicle/<int:vehicle_id>/", views.edit_vehicle, name="edit_vehicle"),
    path(
        "upload-operator-document/<int:vehicle_id>/",
        views.upload_operator_document,
        name="upload_operator_document",
    ),
    path(
        "remove-vehicle-operator/<int:vehicle_id>/<int:operator_id>/",
        views.remove_vehicle_operator,
        name="remove_vehicle_operator",
    ),
    path("search-users/", views.search_users, name="search_users"),
    # Vehicle management (new dashboard)
    path("vehicle-dashboard/", views.vehicle_dashboard, name="vehicle_dashboard"),
    path(
        "add-vehicle-dashboard/",
        views.add_vehicle_dashboard,
        name="add_vehicle_dashboard",
    ),
    path(
        "upload-document-dashboard/",
        views.upload_document_dashboard,
        name="upload_document_dashboard",
    ),
    path(
        "get-vehicle-documents/<int:vehicle_id>/",
        views.get_vehicle_documents,
        name="get_vehicle_documents",
    ),
    path(
        "delete-vehicle-dashboard/<int:vehicle_id>/",
        views.delete_vehicle_dashboard,
        name="delete_vehicle_dashboard",
    ),
    # Vehicle operator assignment
    path(
        "assign-vehicle-operator/<int:vehicle_id>/",
        views.assign_vehicle_operator,
        name="assign_vehicle_operator",
    ),
    path(
        "deactivate-vehicle-operator/<int:assignment_id>/",
        views.deactivate_vehicle_operator,
        name="deactivate_vehicle_operator",
    ),
    path(
        "get-vehicle-operators/<int:vehicle_id>/",
        views.get_vehicle_operators,
        name="get_vehicle_operators",
    ),
    path("search-operators/", views.search_operators, name="search_operators"),
    path(
        "vehicle-operator-history/<int:vehicle_id>/",
        views.vehicle_operator_history,
        name="vehicle_operator_history",
    ),
    # Dashboard operator assignment (AJAX)
    path(
        "assign-operator-dashboard/",
        views.assign_operator_dashboard,
        name="assign_operator_dashboard",
    ),
    path(
        "remove-operator-dashboard/",
        views.remove_operator_dashboard,
        name="remove_operator_dashboard",
    ),
    path(
        "remove-operator-assignment/",
        views.remove_operator_assignment,
        name="remove_operator_assignment",
    ),
    # New operator assignment system
    path(
        "assign-vehicle-operator-new/<int:vehicle_id>/",
        views.assign_vehicle_operator_new,
        name="assign_vehicle_operator_new",
    ),
    path(
        "remove-vehicle-operator-new/<int:assignment_id>/",
        views.remove_vehicle_operator_new,
        name="remove_vehicle_operator_new",
    ),
    # Operator dashboard
    path("operator-dashboard/", views.operator_dashboard, name="operator_dashboard"),
    path(
        "get-operator-vehicles/",
        views.get_operator_vehicles,
        name="get_operator_vehicles",
    ),
    path(
        "get-operator-assignments/<int:operator_id>/",
        views.get_operator_assignments,
        name="get_operator_assignments",
    ),
    # Upload driver license for operators
    path(
        "upload-driver-license/",
        views.upload_driver_license,
        name="upload_driver_license",
    ),
    # Permit management (new workflow)
    path(
        "upload-permit-dashboard/",
        views.upload_permit_dashboard,
        name="upload_permit_dashboard",
    ),
    path("get-permit-status/", views.get_permit_status, name="get_permit_status"),
    # Document management
    path(
        "upload-identity-document/<str:field>/",
        views.upload_identity_document,
        name="upload_identity_document",
    ),
    path(
        "edit-identity-document/<str:field>/",
        views.edit_identity_document,
        name="edit_identity_document",
    ),
    path(
        "edit-vehicle-document/<int:vehicle_id>/<int:document_id>/",
        views.edit_vehicle_document,
        name="edit_vehicle_document",
    ),
    # Permit management
    path("add-permit/", views.add_permit, name="add_permit"),
    path(
        "edit-permit-document/<int:permit_id>/",
        views.edit_permit_document,
        name="edit_permit_document",
    ),
    # Experience management
    path("add-experience/", views.add_experience, name="add_experience"),
    path("update-experience/", views.update_experience, name="update_experience"),
    path("get-experience/<int:exp_id>/", views.get_experience, name="get_experience"),
    path(
        "delete-experience/<int:pk>/", views.delete_experience, name="delete_experience"
    ),
    # Education management
    path("add-education/", views.add_education, name="add_education"),
    path("update-education/", views.update_education, name="update_education"),
    path("get-education/<int:edu_id>/", views.get_education, name="get_education"),
    path("delete-education/<int:pk>/", views.delete_education, name="delete_education"),
    # Portfolio management
    path("add-portfolio/", views.add_portfolio, name="add_portfolio"),
    path("view-portfolio/<int:pk>/", views.view_portfolio, name="view_portfolio"),
    path("edit-portfolio/<int:pk>/", views.edit_portfolio, name="edit_portfolio"),
    path("get-portfolio/<int:pk>/", views.get_portfolio, name="get_portfolio"),
    path("delete-portfolio/<int:pk>/", views.delete_portfolio, name="delete_portfolio"),
    # Skills management
    path("add-skill/", views.add_skill, name="add_skill"),
    path("update-skill/", views.update_skill, name="update_skill"),
    path("get-skill/<int:skill_id>/", views.get_skill, name="get_skill"),
    path("delete-skill/<int:pk>/", views.delete_skill, name="delete_skill"),
    # Availability management
    path("update-availability/", views.update_availability, name="update_availability"),
    # Notifications
    path("fetch-notifications/", views.fetch_notifications, name="fetch_notifications"),
    path("mark-all-as-read/", views.mark_all_as_read, name="mark_all_as_read"),
    
    # CSRF Debug (for troubleshooting)
    path("csrf-debug/", views.csrf_debug_view, name="csrf_debug"),
    path("csrf-test/", views.csrf_test_endpoint, name="csrf_test"),
]
