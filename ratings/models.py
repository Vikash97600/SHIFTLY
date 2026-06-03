from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from matches.models import Match

class RatingReview(models.Model):
    match = models.ForeignKey(Match, on_delete=models.RESTRICT, related_name='reviews')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='reviews_given')
    reviewee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='reviews_received')
    rating = models.DecimalField(
        max_digits=2, 
        decimal_places=1,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)]
    )
    feedback_text = models.TextField(blank=True, null=True)
    categories = models.JSONField(
        blank=True, 
        null=True, 
        help_text="Stores granular scores: e.g., {'punctuality': 5.0, 'skill': 4.0}"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.reviewer.email} -> {self.reviewee.email} ({self.rating} Stars)"
