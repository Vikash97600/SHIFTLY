from django import forms
from .models import BusinessProfile

class BusinessProfileForm(forms.ModelForm):
    class Meta:
        model = BusinessProfile
        fields = [
            'company_name',
            'company_logo_url',
            'website_url',
            'description',
            'industry',
            'business_registration_no',
            'tax_id'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'placeholder': 'Enter company name'
            }),
            'company_logo_url': forms.URLInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'placeholder': 'https://example.com/logo.png'
            }),
            'website_url': forms.URLInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'placeholder': 'https://example.com'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'rows': 4,
                'placeholder': 'Describe your company...'
            }),
            'industry': forms.TextInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'placeholder': 'e.g. Retail, Food Service'
            }),
            'business_registration_no': forms.TextInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'placeholder': 'Registration Number'
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'placeholder': 'Tax ID'
            }),
        }
