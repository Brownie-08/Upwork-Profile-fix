from django.urls import path
from . import views


urlpatterns = [
    path("", views.ProjectListView.as_view(), name="home"),
    path("project/<int:pk>/", views.ProjectDetailView.as_view(), name="project-detail"),
    path(
        "personal_projects/",
        views.PersonalJobsDashboardView.as_view(),
        name="my_projects_dashboard",
    ),
    path("project/create/", views.ProjectCreateView.as_view(), name="project-create"),
    path("project/<int:pk>/proposal/", views.submit_proposal, name="submit-proposal"),
    path(
        "project/<int:project_pk>/accept-proposal/<int:proposal_pk>/",
        views.accept_proposal,
        name="accept-proposal",
    ),
    path("rate-client/<int:project_id>/", views.rate_client, name="rate-client"),
    path(
        "rate-freelancer/<int:project_id>/",
        views.rate_freelancer,
        name="rate-freelancer",
    ),
    path(
        "project/<int:pk>/confirm-completion/",
        views.ProjectCompletionView.as_view(),
        name="project-completion",
    ),
]
