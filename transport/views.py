from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView, CreateView
from django.http import JsonResponse
from django.db.models import Count
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.conf import settings
from googlemaps import Client
from django.db.models import Count, Q
import uuid
import logging
from wallets.models import Wallet, LusitoAccount, Transaction
from notifications.models import Notification
from profiles.models import Vehicle
from .models import TransportRequest, TransportBid, TransportContract, TransportContractTemplate
from .forms import TransportRequestForm, TransportBidForm, TransportRequestFilterForm, TransportContractTemplateForm

logger = logging.getLogger(__name__)

class TransportRequestCreateView(LoginRequiredMixin, CreateView):
    model = TransportRequest
    form_class = TransportRequestForm
    template_name = 'transport/create_transport_request.html'
    success_url = reverse_lazy('transport:job_detail')

    def get_success_url(self):
        return reverse_lazy('transport:job_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['google_maps_api_key'] = settings.GOOGLE_MAPS_CLIENT_API_KEY.get('API_KEY', '')
        return context

    def validate_wallet_balance(self, user, amount):
        try:
            wallet = Wallet.objects.get(user=user)
            if wallet.balance < amount:
                return False, f"Insufficient funds. Available balance: E{wallet.balance:.2f}"
            return True, ""
        except Wallet.DoesNotExist:
            return False, "No wallet found for the user."

    def form_valid(self, form):
        try:
            budget = form.cleaned_data['budget']
            has_funds, error_message = self.validate_wallet_balance(self.request.user, budget)
            if not has_funds:
                messages.error(self.request, error_message)
                return self.form_invalid(form)

            with transaction.atomic():
                job = form.save(commit=False)
                job.client = self.request.user
                job.status = 'OPEN'

                # Fetch route and distance from Google Maps Directions API
                gmaps = Client(key=settings.GOOGLE_MAPS_CLIENT_API_KEY.get('API_KEY'))
                directions = gmaps.directions(
                    origin=(job.pickup_latitude, job.pickup_longitude),
                    destination=(job.dropoff_latitude, job.dropoff_longitude),
                    mode="driving",
                    units="metric"
                )
                if not directions:
                    messages.error(self.request, "Unable to calculate route. Please check the locations.")
                    return self.form_invalid(form)

                route = directions[0]
                job.distance_km = route['legs'][0]['distance']['value'] / 1000  # Convert meters to kilometers
                job.estimated_time = route['legs'][0]['duration']['value'] // 60  # Convert seconds to minutes
                job.route_polyline = route['overview_polyline']['points']  # Save encoded polyline

                job.save()

                messages.success(self.request, f"{job.get_service_type_display()} job created successfully.")
                return super().form_valid(form)

        except Exception as e:
            messages.error(self.request, f"Error creating job: {str(e)}")
            return self.form_invalid(form)

class TransportRequestDetailView(LoginRequiredMixin, DetailView):
    model = TransportRequest
    template_name = 'transport/job_detail.html'
    context_object_name = 'job'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bids'] = self.object.bids.all().order_by('-created_at')
        user_bid = self.object.bids.filter(provider=self.request.user).first() if self.request.user != self.object.client else None
        context['bid_form'] = TransportBidForm(job=self.object) if self.request.user != self.object.client and not user_bid and self.object.status == 'OPEN' else None
        context['user_bid'] = user_bid
        context['can_bid'] = TransportBid(provider=self.request.user, transport_job=self.object).can_bid()
        context['google_maps_api_key'] = settings.GOOGLE_MAPS_CLIENT_API_KEY.get('API_KEY', '')
        if hasattr(self.object, 'contract'):
            context['contract_terms'] = self.object.contract.terms
        context['route_polyline'] = self.object.route_polyline
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            form = TransportBidForm(request.POST, request.FILES, job=self.object)
            if form.is_valid():
                if not TransportBid(provider=request.user, transport_job=self.object).can_bid():
                    return JsonResponse({
                        'status': 'error',
                        'errors': {'__all__': ['You must be a verified provider for this service.']}
                    }, status=403)
                with transaction.atomic():
                    bid = form.save(commit=False)
                    bid.provider = request.user
                    bid.transport_job = self.object
                    bid.save()

                    bid_html = render_to_string('transport/bid_item.html', {'bid': bid}, request=request)
                    return JsonResponse({
                        'status': 'success',
                        'bid_html': bid_html,
                        'message': 'Bid submitted successfully!'
                    })
            else:
                return JsonResponse({
                    'status': 'error',
                    'errors': form.errors
                }, status=400)
        return self.get(request, *args, **kwargs)


class TransportRequestDashboardView(LoginRequiredMixin, ListView):
    template_name = 'transport/transport_dashboard.html'
    context_object_name = 'transport_requests'
    paginate_by = 10

    def get_queryset(self):
        logger.info(f"Dashboard accessed by user: {self.request.user.username}, URL: {self.request.get_full_path()}")
        queryset = TransportRequest.objects.filter(status='OPEN').annotate(bids_count=Count('bids')).order_by('-created_at')
        logger.info(f"Initial open requests count: {queryset.count()}")

        form = TransportRequestFilterForm(self.request.GET)
        if form.is_valid():
            logger.info(f"Form cleaned data: {form.cleaned_data}")
            if form.cleaned_data['service_type']:
                queryset = queryset.filter(service_type=form.cleaned_data['service_type'])
                logger.info(f"After service_type filter: {queryset.count()}")
            if form.cleaned_data['pickup_time_from']:
                queryset = queryset.filter(pickup_time__gte=form.cleaned_data['pickup_time_from'])
                logger.info(f"After pickup_time_from filter: {queryset.count()}")
            if form.cleaned_data['pickup_time_to']:
                queryset = queryset.filter(pickup_time__lte=form.cleaned_data['pickup_time_to'])
                logger.info(f"After pickup_time_to filter: {queryset.count()}")

        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(pickup_location__icontains=search) | 
                Q(dropoff_location__icontains=search)
            )
            logger.info(f"After search filter: {queryset.count()}")

        logger.info(f"Final queryset count: {queryset.count()}")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = TransportRequestFilterForm(self.request.GET)
        context['can_provide_service'] = hasattr(self.request.user, 'profile') and self.request.user.profile.is_identity_verified and self.request.user.profile.account_type == 'PROVIDER'
        context['google_maps_api_key'] = settings.GOOGLE_MAPS_CLIENT_API_KEY.get('API_KEY', '')
        context['filters_applied'] = any(self.request.GET.get(k) for k in ['search', 'service_type', 'pickup_time_from', 'pickup_time_to'])
        logger.info(f"Context: filters_applied={context['filters_applied']}, can_provide_service={context['can_provide_service']}")
        return context

class TransportContractTemplateCreateView(LoginRequiredMixin, CreateView):
    model = TransportContractTemplate
    form_class = TransportContractTemplateForm
    template_name = 'transport/contract_template_form.html'
    success_url = reverse_lazy('transport:contract_template_create')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'You are not authorized to manage contract templates.')
            return redirect('transport:transport_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Deactivate other templates for the same service type
                TransportContractTemplate.objects.filter(
                    service_type=form.cleaned_data['service_type'],
                    is_active=True
                ).exclude(id=form.instance.id).update(is_active=False)
                messages.success(self.request, 'Contract template created successfully.')
                return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f"Error creating template: {str(e)}")
            return self.form_invalid(form)

@login_required
def submit_bid(request, job_id):
    job = get_object_or_404(TransportRequest, id=job_id)
    if request.method == 'POST':
        if not TransportBid(provider=request.user, transport_job=job).can_bid():
            messages.error(request, 'You must be a verified provider to submit bids.')
            return redirect('transport:job_detail', pk=job_id)
        form = TransportBidForm(request.POST, request.FILES, job=job)
        if form.is_valid():
            try:
                with transaction.atomic():
                    bid = form.save(commit=False)
                    bid.transport_job = job
                    bid.provider = request.user
                    bid.save()
                    messages.success(request, 'Bid submitted successfully!')
            except Exception as e:
                messages.error(request, f"Error submitting bid: {str(e)}")
        else:
            messages.error(request, 'Please correct the errors in the bid form.')
    return redirect('transport:job_detail', pk=job_id)

@login_required
def accept_bid(request, bid_id):
    bid = get_object_or_404(TransportBid, id=bid_id)
    job = bid.transport_job
    if request.user != job.client or job.status != 'OPEN':
        messages.error(request, 'You are not authorized or the job is not open.')
        return redirect('transport:job_detail', pk=job.id)
    try:
        with transaction.atomic():
            template = ContractTemplate.get_template(job.service_type)
            if not template:
                raise ValueError("No active contract template found.")
            terms = template.terms.format(
                service_type=job.get_service_type_display(),
                agreed_amount=bid.amount,
                pickup_location=job.pickup_location,
                dropoff_location=job.dropoff_location,
                client_name=job.client.profile.get_full_name(),
                provider_name=bid.provider.profile.get_full_name(),
                job_id=job.id
            )
            contract = TransportContract.objects.create(
                transport_job=job,
                provider=bid.provider,
                client=request.user,
                agreed_amount=bid.amount,
                terms=terms
            )
            job.status = 'ACCEPTED'
            job.provider = bid.provider
            job.save()
            bid.status = 'ACCEPTED'
            bid.save()
            job.bids.exclude(id=bid_id).update(status='REJECTED')
            messages.success(request, 'Bid accepted and contract created.')
    except Exception as e:
        messages.error(request, f"Error accepting bid: {str(e)}")
    return redirect('transport:job_detail', pk=job.id)

@login_required
def confirm_contract(request, contract_id):
    contract = get_object_or_404(TransportContract, id=contract_id, provider=request.user)
    try:
        with transaction.atomic():
            contract.confirm_contract()
            messages.success(request, 'Contract confirmed.')
    except Exception as e:
        messages.error(request, f"Error confirming contract: {str(e)}")
    return redirect('transport:job_detail', pk=contract.transport_job.id)
