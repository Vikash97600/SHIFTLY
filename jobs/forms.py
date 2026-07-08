from django import forms
from django.utils import timezone
from .models import JobPosting

class JobPostingForm(forms.ModelForm):
    class Meta:
        model = JobPosting
        fields = [
            'title',
            'description',
            'work_type',
            'location_name',
            'latitude',
            'longitude',
            'base_pay',
            'start_date',
            'end_date',
            'shift_start_time',
            'shift_end_time',
            'slots_available'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'placeholder': 'e.g. Specialty Barista Shift'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'rows': 4,
                'placeholder': 'Provide details on tasks, duties, and qualifications...'
            }),
            'work_type': forms.Select(attrs={
                'class': 'form-select bg-dark border-secondary text-light'
            }),
            'location_name': forms.TextInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'placeholder': 'e.g. 120 Market St, San Francisco, CA'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'step': '0.000001',
                'placeholder': '37.7749'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'step': '0.000001',
                'placeholder': '-122.4194'
            }),
            'base_pay': forms.NumberInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'step': '0.50',
                'placeholder': '20.00'
            }),
            'rate_type': forms.Select(attrs={
                'class': 'form-select bg-dark border-secondary text-light'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'type': 'date'
            }),
            'shift_start_time': forms.TimeInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'type': 'time'
            }),
            'shift_end_time': forms.TimeInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'type': 'time'
            }),
            'slots_available': forms.NumberInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'min': '1',
                'placeholder': '1'
            }),
        }

    def clean_base_pay(self):
        pay = self.cleaned_data.get('base_pay')
        if pay is not None and pay <= 0:
            raise forms.ValidationError("Base pay must be a positive number.")
        return pay

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        shift_start_time = cleaned_data.get('shift_start_time')
        shift_end_time = cleaned_data.get('shift_end_time')

        if start_date and end_date:
            if start_date < timezone.now().date():
                self.add_error('start_date', "Start date cannot be in the past.")
            if start_date > end_date:
                self.add_error('end_date', "End date must be on or after start date.")

        if start_date == end_date and shift_start_time and shift_end_time:
            if shift_start_time >= shift_end_time:
                self.add_error('shift_end_time', "Shift end time must be after start time on the same day.")

        return cleaned_data
