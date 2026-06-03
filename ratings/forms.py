from django import forms
from .models import RatingReview

class RatingReviewForm(forms.ModelForm):
    class Meta:
        model = RatingReview
        fields = ['rating', 'feedback_text']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'min': '1.0',
                'max': '5.0',
                'step': '0.5',
                'placeholder': 'Enter rating (1.0 - 5.0)'
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
