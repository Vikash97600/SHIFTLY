from django import forms
from .models import StudentProfile

class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = [
            'first_name', 
            'last_name', 
            'bio', 
            'hourly_rate_expectation', 
            'availability_status', 
            'resume', 
            'portfolio_file'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'placeholder': 'Enter last name'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'rows': 4,
                'placeholder': 'Tell us about your professional background, skills, and availability...'
            }),
            'hourly_rate_expectation': forms.NumberInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'step': '0.50',
                'placeholder': 'e.g. 20.00'
            }),
            'availability_status': forms.Select(attrs={
                'class': 'form-select bg-dark border-secondary text-light'
            }),
            'resume': forms.ClearableFileInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light'
            }),
            'portfolio_file': forms.ClearableFileInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light'
            }),
        }

    def clean_hourly_rate_expectation(self):
        rate = self.cleaned_data.get('hourly_rate_expectation')
        if rate is not None and rate < 0:
            raise forms.ValidationError("Expected hourly rate cannot be negative.")
        return rate
