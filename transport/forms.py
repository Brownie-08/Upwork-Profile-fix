from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from profiles.models import Vehicle
from .models import TransportRequest, TransportBid, TransportContractTemplate

class TransportRequestForm(forms.ModelForm):
    class Meta:
        model = TransportRequest
        fields = [
            'service_type', 'pickup_location', 'pickup_latitude', 'pickup_longitude',
            'dropoff_location', 'dropoff_latitude', 'dropoff_longitude', 'pickup_time',
            'budget', 'description', 'load_image', 'is_urgent', 'vehicle_type_required'
        ]
        widgets = {
            'service_type': forms.Select(attrs={'class': 'form-select block w-full border-gray-300 rounded-md'}),
            'pickup_location': forms.TextInput(attrs={'class': 'form-input block w-full border-gray-300 rounded-md', 'placeholder': 'Enter pickup address'}),
            'pickup_latitude': forms.HiddenInput(),
            'pickup_longitude': forms.HiddenInput(),
            'dropoff_location': forms.TextInput(attrs={'class': 'form-input block w-full border-gray-300 rounded-md', 'placeholder': 'Enter dropoff address'}),
            'dropoff_latitude': forms.HiddenInput(),
            'dropoff_longitude': forms.HiddenInput(),
            'pickup_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-input block w-full border-gray-300 rounded-md'}),
            'budget': forms.NumberInput(attrs={'class': 'form-input block w-full border-gray-300 rounded-md', 'step': '0.01', 'min': '0'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea block w-full border-gray-300 rounded-md', 'rows': 4, 'placeholder': 'Describe the job'}),
            'load_image': forms.FileInput(attrs={'class': 'form-input block w-full border-gray-300 rounded-md', 'accept': 'image/jpeg,image/png'}),
            'is_urgent': forms.CheckboxInput(attrs={'class': 'form-checkbox h-4 w-4 text-blue-600'}),
            'vehicle_type_required': forms.Select(attrs={'class': 'form-select block w-full border-gray-300 rounded-md'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Create Job', css_class='w-full bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg px-4 py-2'))

    def clean_load_image(self):
        load_image = self.cleaned_data.get('load_image')
        if load_image:
            if not load_image.content_type in ['image/jpeg', 'image/png']:
                raise forms.ValidationError('Only JPEG or PNG images are allowed.')
            if load_image.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError('Image size must be under 5MB.')
        return load_image

    def clean(self):
        cleaned_data = super().clean()
        service_type = cleaned_data.get('service_type')
        if service_type == 'TAXI':
            cleaned_data['load_image'] = None
            cleaned_data['is_urgent'] = False
            cleaned_data['vehicle_type_required'] = 'ANY'
        elif service_type == 'DELIVERY':
            if not cleaned_data.get('description'):
                self.add_error('description', 'Description is required for delivery jobs.')
        return cleaned_data

class TransportBidForm(forms.ModelForm):
    class Meta:
        model = TransportBid
        fields = ['amount', 'proposal', 'estimated_completion_time', 'vehicle_type', 'job_sample']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-input block w-full border-gray-300 rounded-md', 'step': '0.01', 'min': '0'}),
            'proposal': forms.Textarea(attrs={'class': 'form-textarea block w-full border-gray-300 rounded-md', 'rows': 4, 'placeholder': 'Describe your bid'}),
            'estimated_completion_time': forms.NumberInput(attrs={'class': 'form-input block w-full border-gray-300 rounded-md', 'min': '0', 'placeholder': 'Minutes'}),
            'vehicle_type': forms.Select(attrs={'class': 'form-select block w-full border-gray-300 rounded-md'}),
            'job_sample': forms.FileInput(attrs={'class': 'form-input block w-full border-gray-300 rounded-md'}),
        }

    def __init__(self, *args, job=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.job = job
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Submit Bid', css_class='w-full bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg px-4 py-2'))
        if job and job.service_type == 'TAXI':
            self.fields['vehicle_type'].choices = [('ANY', 'Any Vehicle')]
            self.fields['vehicle_type'].initial = 'ANY'

    def clean_job_sample(self):
        job_sample = self.cleaned_data.get('job_sample')
        if job_sample:
            if job_sample.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError('File size must be under 5MB.')
        return job_sample

    def clean_vehicle_type(self):
        vehicle_type = self.cleaned_data.get('vehicle_type')
        if self.job and self.job.service_type == 'DELIVERY' and self.job.vehicle_type_required != 'ANY':
            if vehicle_type != self.job.vehicle_type_required:
                raise forms.ValidationError(f'Vehicle type must be {self.job.vehicle_type_required}.')
        return vehicle_type

class TransportRequestFilterForm(forms.Form):
    SERVICE_TYPE_CHOICES = [('', 'Any Service')] + TransportRequest.SERVICE_TYPE_CHOICES

    service_type = forms.ChoiceField(
        choices=SERVICE_TYPE_CHOICES,
        required=False,
        label='Service Type'
    )
    pickup_time_from = forms.DateTimeField(
        required=False,
        label='Pickup Time From',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )
    pickup_time_to = forms.DateTimeField(
        required=False,
        label='Pickup Time To',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.attrs = {'class': 'space-y-4 bg-white p-6 rounded-xl shadow-md'}
        self.helper.add_input(Submit('submit', 'Apply Filters', css_class='w-full bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg px-4 py-2'))

    def clean(self):
        cleaned_data = super().clean()
        pickup_time_from = cleaned_data.get('pickup_time_from')
        pickup_time_to = cleaned_data.get('pickup_time_to')

        # Validate pickup time range
        if pickup_time_from and pickup_time_to and pickup_time_from > pickup_time_to:
            self.add_error('pickup_time_to', "Pickup Time From cannot be later than Pickup Time To.")

        return cleaned_data

    def clean_pickup_time_to(self):
        """Ensures pickup_time_to is not later than 3 days, 12 hours, and 30 minutes from now."""
        pickup_time_to = self.cleaned_data.get('pickup_time_to')
        if pickup_time_to:
            max_limit = timezone.now() + timedelta(days=3, hours=12, minutes=30)
            if pickup_time_to > max_limit:
                raise forms.ValidationError("Pickup time cannot be later than 3 days, 12 hours, and 30 minutes from now.")
        return pickup_time_to

class TransportContractTemplateForm(forms.ModelForm):
    class Meta:
        model = TransportContractTemplate
        fields = ['service_type', 'terms', 'is_active']
        widgets = {
            'service_type': forms.Select(attrs={'class': 'form-select block w-full border-gray-300 rounded-md'}),
            'terms': forms.Textarea(attrs={'class': 'form-textarea block w-full border-gray-300 rounded-md', 'rows': 6, 'placeholder': 'Enter contract terms with placeholders'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox h-4 w-4 text-blue-600'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Save Template', css_class='w-full bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg px-4 py-2'))

    def clean_terms(self):
        terms = self.cleaned_data.get('terms')
        required_placeholders = ['{service_type}', '{agreed_amount}', '{pickup_location}', '{dropoff_location}', '{client_name}', '{provider_name}', '{job_id}']
        missing = [ph for ph in required_placeholders if ph not in terms]
        if missing:
            raise forms.ValidationError(f"Terms must include placeholders: {', '.join(missing)}")
        return terms