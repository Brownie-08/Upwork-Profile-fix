from django import forms
from .models import Project, Proposal, ProposalFile, ProjectFile, Rating


class ProjectForm(forms.ModelForm):
    """Form for creating a new project with optional multiple file uploads."""

    files = forms.FileField(required=False, widget=forms.ClearableFileInput())
    service_type = forms.ChoiceField(
        choices=Project.SERVICE_TYPE_CHOICES,
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Project
        fields = ["title", "description", "budget", "service_type", "deadline"]
        widgets = {
            "deadline": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
        }


class ProjectFileForm(forms.ModelForm):
    """Form for managing Project files."""

    class Meta:
        model = ProjectFile
        fields = ["file", "file_name", "file_type"]


class ProposalFileForm(forms.ModelForm):
    class Meta:
        model = ProposalFile
        fields = ["file", "description"]
        widgets = {
            "description": forms.Textarea(
                attrs={"rows": 2, "placeholder": "Briefly describe this sample work"}
            )
        }


class ProposalForm(forms.ModelForm):
    sample_works = forms.FileField(
        widget=forms.ClearableFileInput(),
        required=False,
        help_text="Upload up to 5 files (5MB max per file). Accepted formats: PDF, DOC, DOCX, TXT, PNG, JPG, JPEG, ZIP",
    )

    class Meta:
        model = Proposal
        fields = ["proposal_text", "bid_amount"]
        widgets = {
            "proposal_text": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": "Describe your approach, experience, and why you're the best fit for this project",
                }
            ),
            "bid_amount": forms.NumberInput(
                attrs={"placeholder": "Enter your bid amount"}
            ),
        }

    def clean_sample_works(self):
        files = self.files.getlist("sample_works")
        if len(files) > 5:
            raise forms.ValidationError("You can upload a maximum of 5 files.")

        for file in files:
            if file.size > 5485760:  # 5MB
                raise forms.ValidationError(
                    f"File {file.name} is too large. Maximum size is 10MB."
                )

            ext = file.name.split(".")[-1].lower()
            allowed_extensions = [
                "pdf",
                "doc",
                "docx",
                "txt",
                "png",
                "jpg",
                "jpeg",
                "zip",
            ]
            if ext not in allowed_extensions:
                raise forms.ValidationError(f"File type .{ext} is not supported.")

        return files


# ratings
class ClientRatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.HiddenInput(),
            "comment": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Leave a comment..."}
            ),
        }


class FreelancerRatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.HiddenInput(),
            "comment": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Leave a comment..."}
            ),
        }


class CompletionConfirmationForm(forms.Form):
    confirm = forms.BooleanField(
        required=True,
        label="I confirm completion of this project.",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
