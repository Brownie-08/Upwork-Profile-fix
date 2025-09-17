from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
)
from django.db.models import Q
from django.views import View
from django.utils.timezone import now
from django.db import transaction
from decimal import Decimal
from django.urls import reverse_lazy
import uuid
from django.contrib import messages
from .forms import (
    ProposalForm,
    ProjectForm,
    ClientRatingForm,
    FreelancerRatingForm,
)
from .models import Project, ProjectFile, Proposal
from wallets.models import Wallet, Transaction, LusitoAccount

# Create your views here.


class ProjectListView(ListView):
    model = Project
    template_name = "core/home.html"
    context_object_name = "projects"
    ordering = ["-created_at"]
    paginate_by = 10

    def get_queryset(self):
        # Base queryset
        queryset = Project.objects.filter(status="OPEN").order_by("-created_at")

        # Get filter parameters
        service_type = self.request.GET.get("service_type")
        budget = self.request.GET.get("budget")
        status = self.request.GET.get("status")

        # Apply filters
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        if budget:
            queryset = queryset.filter(budget__lte=budget)
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        # Get default context
        context = super().get_context_data(**kwargs)

        # Add filter values and service type choices
        context["selected_service_type"] = self.request.GET.get("service_type", "")
        context["selected_budget"] = self.request.GET.get("budget", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["service_type_choices"] = Project.SERVICE_TYPE_CHOICES

        return context


class ProjectDetailView(DetailView):
    model = Project
    template_name = "projects/project_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["proposal_form"] = ProposalForm()
        context["proposals"] = self.object.proposals.all()
        context["files"] = self.object.files.all()  # Project files
        context["form"] = ProjectFile()  # File upload form
        return context

    def post(self, request, *args, **kwargs):
        project = self.get_object()

        form = ProjectFile(request.POST, request.FILES)
        if form.is_valid():
            # Handle multiple file uploads
            uploaded_files = request.FILES.getlist("files")
            for uploaded_file in uploaded_files:
                project_file = ProjectFile(
                    project=project,
                    file=uploaded_file,
                    file_name=uploaded_file.name,
                    file_size=uploaded_file.size,
                    file_type=uploaded_file.content_type,
                )
                project_file.save()  # Save the file to the database
            return redirect(
                "project-detail", pk=project.pk
            )  # Redirect to project detail page
        return self.render_to_response({"form": form})


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"
    success_url = reverse_lazy(
        "project-list"
    )  # Redirect to project list after creation

    def validate_wallet_balance(self, user, amount):
        """
        Validate if user has sufficient balance in wallet.
        Returns (bool, str) tuple indicating success and message.
        """
        try:
            wallet = Wallet.objects.get(user=user)
            if wallet.balance < amount:
                return (
                    False,
                    f"Insufficient funds. Available balance: ${wallet.balance:.2f}",
                )
            return True, "Sufficient funds available."
        except Wallet.DoesNotExist:
            return False, "No wallet found for the user."

    def form_valid(self, form):
        try:
            # Get the budget amount from the form
            budget = form.cleaned_data["budget"]

            # Validate wallet balance
            has_funds, message = self.validate_wallet_balance(self.request.user, budget)
            if not has_funds:
                messages.error(self.request, message)
                return self.form_invalid(form)

            # Start transaction to ensure atomicity
            with transaction.atomic():
                # Save the project instance
                project = form.save(commit=False)
                project.client = self.request.user
                project.status = "OPEN"
                project.save()

                # Hold funds in LusitoAccount
                site_account = LusitoAccount.objects.first()
                if site_account:
                    # Deduct amount from user's wallet
                    site_account.hold_project_funds(budget)
                    wallet = Wallet.objects.get(user=self.request.user)
                    wallet.balance -= Decimal(str(budget))
                    wallet.save()

                    # Create transaction record
                    Transaction.objects.create(
                        wallet=wallet,
                        transaction_type="PAYMENT",
                        amount=budget,
                        status="COMPLETED",
                        description=f"Payment for project: {project.title}",
                        reference_id=str(uuid.uuid4()),
                    )

                    # Process file uploads
                    files = self.request.FILES.getlist("files")
                    for uploaded_file in files:
                        try:
                            project.validate_file(uploaded_file)
                            project_file = ProjectFile(
                                project=project, file=uploaded_file
                            )
                            project_file.save()
                        except ValueError as e:
                            raise ValidationError(str(e))

                    messages.success(
                        self.request,
                        "Project created successfully, and funds have been held.",
                    )
                    return redirect("project-detail", pk=project.pk)
                else:
                    raise ValidationError("Unable to hold funds in LusitoAccount.")

        except Exception as e:
            messages.error(self.request, f"Error processing project creation: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            wallet = Wallet.objects.get(user=self.request.user)
            context["wallet_balance"] = wallet.balance
        except Wallet.DoesNotExist:
            context["wallet_balance"] = 0
        return context


@login_required
def submit_proposal(request, pk):
    project = get_object_or_404(Project, pk=pk)

    # Ensure only open projects can receive proposals
    if project.status != "OPEN":
        messages.error(request, "Proposals are not allowed for this project.")
        return redirect("project-detail", pk=pk)

    if request.method == "POST":
        form = ProposalForm(request.POST)
        if form.is_valid():
            # Check if a proposal already exists for this freelancer and project
            existing_proposal = Proposal.objects.filter(
                project=project, freelancer=request.user
            ).exists()

            if existing_proposal:
                messages.info(
                    request, "You have already submitted a proposal for this project."
                )
                return redirect("project-detail", pk=pk)

            # Save the proposal
            proposal = form.save(commit=False)
            proposal.project = project
            proposal.freelancer = request.user
            proposal.save()

            messages.success(request, "Your proposal has been submitted!")
            return redirect("project-detail", pk=pk)

    messages.error(request, "Invalid form submission.")
    return redirect("project-detail", pk=pk)


@login_required
def accept_proposal(request, project_pk, proposal_pk):
    project = get_object_or_404(Project, pk=project_pk)
    proposal = get_object_or_404(Proposal, pk=proposal_pk)

    if request.user == project.client and project.status == "OPEN":
        project.freelancer = proposal.freelancer
        project.status = "IN_PROGRESS"
        project.budget = proposal.bid_amount
        project.save()
        proposal.accepted = True
        proposal.save()
        messages.success(request, "Proposal accepted! Project status updated.")
    return redirect("project-detail", pk=project_pk)


class PersonalJobsDashboardView(ListView):
    model = Project
    template_name = "projects/my_jobs.html"
    context_object_name = "projects"

    def get_queryset(self):
        return (
            Project.objects.none()
        )  # Returning an empty QuerySet because we are overriding context data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Active (In Progress) jobs: For both freelancers and clients
        active_jobs = Project.objects.filter(
            (Q(freelancer=user) | Q(client=user)) & Q(status="IN_PROGRESS")
        ).order_by("-deadline")

        # Completed jobs: For both freelancers and clients
        completed_jobs = Project.objects.filter(
            (Q(freelancer=user) | Q(client=user)) & Q(status="COMPLETED")
        ).order_by("-completion_date")

        # Issued (Open) jobs: Only for the client
        issued_jobs = Project.objects.filter(client=user, status="OPEN").order_by(
            "-created_at"
        )
        # Pass them into the context
        context["active_jobs"] = active_jobs
        context["completed_jobs"] = completed_jobs
        context["issued_jobs"] = issued_jobs

        return context


# rating views
@login_required
def rate_client(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    # Ensure the project status is 'COMPLETED'
    if project.status != "COMPLETED":
        raise PermissionDenied("You can only rate a project that has been completed.")

    if request.method == "POST":
        form = FreelancerRatingForm(request.POST)
        if form.is_valid():
            # Ensure that the client is the one submitting the rating
            if request.user != project.client:
                raise PermissionDenied("Only the client can rate the freelancer.")

            rating = form.save(commit=False)
            rating.project = project
            rating.rated_by = request.user
            rating.rater_type = "CLIENT"
            rating.save()
            return redirect("project-detail", pk=project_id)

    form = FreelancerRatingForm()
    return render(
        request,
        "projects/rating.html",
        {"form": form, "project": project, "user_type": "client"},
    )


@login_required
def rate_freelancer(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    # Ensure the project status is 'COMPLETED'
    if project.status != "COMPLETED":
        raise PermissionDenied("You can only rate a project that has been completed.")

    if request.method == "POST":
        form = ClientRatingForm(request.POST)
        if form.is_valid():
            # Ensure that the freelancer is the one submitting the rating
            if request.user != project.freelancer:
                raise PermissionDenied("Only the freelancer can rate the client.")

            rating = form.save(commit=False)
            rating.project = project
            rating.rated_by = request.user
            rating.rater_type = "FREELANCER"
            rating.save()
            return redirect("project-detail", pk=project_id)

    form = ClientRatingForm()
    return render(
        request,
        "projects/rating.html",
        {"form": form, "project": project, "user_type": "freelancer"},
    )


class ProjectCompletionView(LoginRequiredMixin, View):
    template_name = "projects/project_completion.html"

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)

        # Ensure only the client or freelancer can access this page
        if request.user != project.client and request.user != project.freelancer:
            messages.error(request, "Unauthorized access")
            return redirect("project-list")

        context = {
            "project": project,
            "is_client": request.user == project.client,
            "is_freelancer": request.user == project.freelancer,
            "awaiting_other": (
                request.user == project.client and project.freelancer_confirmed
            )
            or (request.user == project.freelancer and project.client_confirmed),
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)

        # Ensure only the client or freelancer can confirm completion
        if request.user != project.client and request.user != project.freelancer:
            messages.error(request, "Unauthorized action")
            return redirect("project-list")

        # Update confirmation status
        if request.user == project.client:
            project.client_confirmed = True
        elif request.user == project.freelancer:
            project.freelancer_confirmed = True

        project.save()

        # Check if both parties have confirmed completion
        if project.is_completed():
            try:
                # Calculate commission and freelancer payment
                commission_rate = Decimal("0.10")  # 10% commission
                commission = project.budget * commission_rate
                freelancer_payment = project.budget - commission

                # Update LusitoAccount balances
                site_account = LusitoAccount.objects.first()
                if not site_account:
                    messages.error(request, "Lusito Account not found")
                    return redirect("project-detail", pk=project.pk)

                site_account.held_funds -= project.budget
                site_account.commission_balance += commission
                site_account.total_balance -= freelancer_payment
                site_account.save()

                # Add payment to freelancer's wallet
                freelancer_wallet = Wallet.objects.get(user=project.freelancer)
                freelancer_wallet.balance += freelancer_payment
                freelancer_wallet.save()

                # Record freelancer payment transaction
                Transaction.objects.create(
                    wallet=freelancer_wallet,
                    transaction_type="PAYMENT",
                    amount=freelancer_payment,
                    status="COMPLETED",
                    description=f"Payment for project: {project.title}",
                    reference_id=str(uuid.uuid4()),
                    timestamp=now(),
                )

                # Record commission transaction
                Transaction.objects.create(
                    wallet=None,  # Platform account, not tied to a user wallet
                    transaction_type="COMMISSION",
                    amount=commission,
                    status="COMPLETED",
                    description=f"Commission for project: {project.title}",
                    reference_id=str(uuid.uuid4()),
                    timestamp=now(),
                )

                # Mark project as completed
                project.status = "COMPLETED"
                project.completion_date = now()  # Add completion timestamp
                project.save()

                messages.success(
                    request,
                    "Project completed successfully. Funds have been released to the freelancer.",
                )
                return redirect("project-detail", pk=project.pk)

            except Exception as e:
                messages.error(request, f"Error processing completion: {str(e)}")
                return redirect("project-detail", pk=project.pk)

        messages.info(
            request, "Confirmation recorded. Awaiting the other party's confirmation."
        )
        return redirect("project-detail", pk=project.pk)
