from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from matches.models import Match
from students.models import StudentProfile
from businesses.models import BusinessProfile

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


class StudentReputation(models.Model):
    student = models.OneToOneField(StudentProfile, on_delete=models.CASCADE, related_name='reputation')
    attendance_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    punctuality_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    cancellation_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    professional_score = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    experience_bonus = models.IntegerField(default=0)
    reputation_score = models.IntegerField(default=100)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reputation of {self.student}: {self.reputation_score}"

    @property
    def trust_level(self):
        score = self.reputation_score
        if score >= 95:
            return "Elite Professional"
        elif score >= 90:
            return "Gold Worker"
        elif score >= 80:
            return "Trusted Worker"
        elif score >= 70:
            return "Reliable Worker"
        elif score >= 60:
            return "Improving"
        else:
            return "Needs Improvement"

    @property
    def trust_badge(self):
        score = self.reputation_score
        if score >= 95:
            return "👑 Elite Professional"
        elif score >= 90:
            return "🏆 Gold Worker"
        elif score >= 80:
            return "⭐ Trusted Worker"
        elif score >= 70:
            return "🔷 Reliable Worker"
        elif score >= 60:
            return "🟡 Improving"
        else:
            return "🔴 Needs Improvement"


class StudentReputationHistory(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='reputation_history')
    reputation_score = models.IntegerField()
    attendance_rate = models.DecimalField(max_digits=5, decimal_places=2)
    punctuality_rate = models.DecimalField(max_digits=5, decimal_places=2)
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2)
    cancellation_rate = models.DecimalField(max_digits=5, decimal_places=2)
    professional_score = models.DecimalField(max_digits=5, decimal_places=2)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2)
    experience_bonus = models.IntegerField()
    change_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class BusinessReputation(models.Model):
    business = models.OneToOneField(BusinessProfile, on_delete=models.CASCADE, related_name='reputation')
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    payment_timeliness_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    job_accuracy_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    cancellation_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    complaint_resolution_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    reputation_score = models.IntegerField(default=100)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reputation of {self.business}: {self.reputation_score}"

    @property
    def trust_level(self):
        score = self.reputation_score
        if score >= 95:
            return "Elite Employer"
        elif score >= 90:
            return "Gold Employer"
        elif score >= 80:
            return "Trusted Employer"
        elif score >= 70:
            return "Reliable Employer"
        elif score >= 60:
            return "Improving"
        else:
            return "Needs Improvement"

    @property
    def trust_badge(self):
        score = self.reputation_score
        if score >= 95:
            return "👑 Elite Employer"
        elif score >= 90:
            return "🏆 Gold Employer"
        elif score >= 80:
            return "⭐ Trusted Employer"
        elif score >= 70:
            return "🔷 Reliable Employer"
        elif score >= 60:
            return "🟡 Improving"
        else:
            return "🔴 Needs Improvement"


class BusinessReputationHistory(models.Model):
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='reputation_history')
    reputation_score = models.IntegerField()
    average_rating = models.DecimalField(max_digits=3, decimal_places=2)
    payment_timeliness_rate = models.DecimalField(max_digits=5, decimal_places=2)
    job_accuracy_rate = models.DecimalField(max_digits=5, decimal_places=2)
    cancellation_rate = models.DecimalField(max_digits=5, decimal_places=2)
    complaint_resolution_rate = models.DecimalField(max_digits=5, decimal_places=2)
    change_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
