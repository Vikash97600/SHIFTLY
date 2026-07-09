from django import forms
from django.utils import timezone
from .models import JobPosting

class JobPostingForm(forms.ModelForm):
    hiring_radius = forms.ChoiceField(
        choices=[
            ('2.00', '2 KM'),
            ('3.00', '3 KM'),
            ('4.00', '4 KM'),
            ('5.00', '5 KM'),
            ('10.00', '10 KM'),
            ('15.00', '15 KM'),
            ('50.00', 'Entire City (Premium)'),
            ('999.00', 'Remote (No Distance Limit)')
        ],
        initial='4.00',
        widget=forms.Select(attrs={
            'class': 'form-select bg-dark border-secondary text-light',
            'id': 'id_hiring_radius'
        })
    )

    class Meta:
        model = JobPosting
        fields = [
            'title',
            'description',
            'category',
            'job_mode',
            'hiring_radius',
            'is_urgent',
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
            'category': forms.Select(attrs={
                'class': 'form-select bg-dark border-secondary text-light',
                'id': 'id_category'
            }),
            'job_mode': forms.Select(attrs={
                'class': 'form-select bg-dark border-secondary text-light',
                'id': 'id_job_mode'
            }),
            'is_urgent': forms.CheckboxInput(attrs={
                'class': 'form-check-input bg-dark border-secondary',
                'role': 'switch',
                'id': 'id_is_urgent'
            }),
            'location_name': forms.TextInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'placeholder': 'e.g. 120 Market St, San Francisco, CA',
                'id': 'id_location_name'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'step': '0.000001',
                'placeholder': '37.7749',
                'id': 'id_latitude'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'step': '0.000001',
                'placeholder': '-122.4194',
                'id': 'id_longitude'
            }),
            'base_pay': forms.NumberInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'step': '0.50',
                'placeholder': '20.00'
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make location fields optional for remote jobs
        self.fields['location_name'].required = False
        self.fields['latitude'].required = False
        self.fields['longitude'].required = False

    def clean_base_pay(self):
        pay = self.cleaned_data.get('base_pay')
        if pay is not None and pay <= 0:
            raise forms.ValidationError("Base pay must be a positive number.")
        return pay

    def clean(self):
        cleaned_data = super().clean()
        job_mode = cleaned_data.get('job_mode')
        
        # If remote, populate default location fields to satisfy DB constraints
        if job_mode == 'remote':
            cleaned_data['latitude'] = cleaned_data.get('latitude') or 0.0
            cleaned_data['longitude'] = cleaned_data.get('longitude') or 0.0
            cleaned_data['location_name'] = cleaned_data.get('location_name') or 'Remote'
            
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

