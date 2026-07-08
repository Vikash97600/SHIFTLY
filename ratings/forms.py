from django import forms
from .models import RatingReview

class RatingReviewForm(forms.ModelForm):
    attendance = forms.ChoiceField(
        choices=[('present', 'Present / Attended'), ('absent', 'Absent / No-Show')],
        widget=forms.Select(attrs={'class': 'form-select bg-dark border-secondary text-light'}),
        initial='present'
    )
    punctuality = forms.ChoiceField(
        choices=[
            ('early', 'Early'),
            ('on_time', 'On Time'),
            ('late_1_10', 'Late (1-10 min)'),
            ('late_10_20', 'Late (10-20 min)'),
            ('very_late', 'Very Late (>20 min)'),
        ],
        widget=forms.Select(attrs={'class': 'form-select bg-dark border-secondary text-light'}),
        initial='on_time'
    )
    communication = forms.IntegerField(
        min_value=1, max_value=5, initial=5,
        widget=forms.NumberInput(attrs={'class': 'form-control bg-dark border-secondary text-light', 'min': 1, 'max': 5})
    )
    behaviour = forms.IntegerField(
        min_value=1, max_value=5, initial=5,
        widget=forms.NumberInput(attrs={'class': 'form-control bg-dark border-secondary text-light', 'min': 1, 'max': 5})
    )
    teamwork = forms.IntegerField(
        min_value=1, max_value=5, initial=5,
        widget=forms.NumberInput(attrs={'class': 'form-control bg-dark border-secondary text-light', 'min': 1, 'max': 5})
    )
    work_quality = forms.IntegerField(
        min_value=1, max_value=5, initial=5,
        widget=forms.NumberInput(attrs={'class': 'form-control bg-dark border-secondary text-light', 'min': 1, 'max': 5})
    )
    professionalism = forms.IntegerField(
        min_value=1, max_value=5, initial=5,
        widget=forms.NumberInput(attrs={'class': 'form-control bg-dark border-secondary text-light', 'min': 1, 'max': 5})
    )

    class Meta:
        model = RatingReview
        fields = ['rating', 'feedback_text']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'min': '1.0',
                'max': '5.0',
                'step': '0.5',
                'placeholder': 'Enter overall rating (1.0 - 5.0)'
            }),
            'feedback_text': forms.Textarea(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'rows': 4,
                'placeholder': 'Provide feedback on user performance, punctuality, and attitude...'
            }),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating is not None and (rating < 1.0 or rating > 5.0):
            raise forms.ValidationError("Rating must be between 1.0 and 5.0 stars.")
        return rating

    def save(self, commit=True):
        instance = super().save(commit=False)
        cats = {
            'attendance': self.cleaned_data.get('attendance'),
            'punctuality': self.cleaned_data.get('punctuality'),
            'communication': int(self.cleaned_data.get('communication') or 5),
            'behaviour': int(self.cleaned_data.get('behaviour') or 5),
            'teamwork': int(self.cleaned_data.get('teamwork') or 5),
            'work_quality': int(self.cleaned_data.get('work_quality') or 5),
            'professionalism': int(self.cleaned_data.get('professionalism') or 5),
        }
        instance.categories = cats
        if commit:
            instance.save()
        return instance


class BusinessRatingReviewForm(forms.ModelForm):
    payment_timeliness = forms.IntegerField(
        min_value=1, max_value=5, initial=5,
        widget=forms.NumberInput(attrs={'class': 'form-control bg-dark border-secondary text-light', 'min': 1, 'max': 5})
    )
    job_accuracy = forms.IntegerField(
        min_value=1, max_value=5, initial=5,
        widget=forms.NumberInput(attrs={'class': 'form-control bg-dark border-secondary text-light', 'min': 1, 'max': 5})
    )
    work_environment = forms.IntegerField(
        min_value=1, max_value=5, initial=5,
        widget=forms.NumberInput(attrs={'class': 'form-control bg-dark border-secondary text-light', 'min': 1, 'max': 5})
    )
    communication = forms.IntegerField(
        min_value=1, max_value=5, initial=5,
        widget=forms.NumberInput(attrs={'class': 'form-control bg-dark border-secondary text-light', 'min': 1, 'max': 5})
    )

    class Meta:
        model = RatingReview
        fields = ['rating', 'feedback_text']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'min': '1.0',
                'max': '5.0',
                'step': '0.5',
                'placeholder': 'Enter overall rating (1.0 - 5.0)'
            }),
            'feedback_text': forms.Textarea(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'rows': 4,
                'placeholder': 'Provide feedback on employer coordination, environment, and pay speed...'
            }),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating is not None and (rating < 1.0 or rating > 5.0):
            raise forms.ValidationError("Rating must be between 1.0 and 5.0 stars.")
        return rating

    def save(self, commit=True):
        instance = super().save(commit=False)
        cats = {
            'payment_timeliness': int(self.cleaned_data.get('payment_timeliness') or 5),
            'job_accuracy': int(self.cleaned_data.get('job_accuracy') or 5),
            'work_environment': int(self.cleaned_data.get('work_environment') or 5),
            'communication': int(self.cleaned_data.get('communication') or 5),
        }
        instance.categories = cats
        if commit:
            instance.save()
        return instance
