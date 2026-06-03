import uuid
from django.db import models
from students.models import StudentProfile
from jobs.models import JobPosting

class Match(models.Model):
    class MatchStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        UNMATCHED = 'unmatched', 'Unmatched'
        HIRED = 'hired', 'Hired'

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.RESTRICT, related_name='matches')
    job = models.ForeignKey(JobPosting, on_delete=models.RESTRICT, related_name='matches')
    status = models.CharField(max_length=20, choices=MatchStatus.choices, default=MatchStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'job')

    def __str__(self):
        return f"Match: {self.student} <-> {self.job.title} ({self.status})"


class JobApplication(models.Model):
    class ApplicationStatus(models.TextChoices):
        APPLIED = 'applied', 'Applied'
        SHORTLISTED = 'shortlisted', 'Shortlisted'
        OFFERED = 'offered', 'Offered'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    match = models.OneToOneField(Match, on_delete=models.SET_NULL, null=True, blank=True, related_name='application')
    student = models.ForeignKey(StudentProfile, on_delete=models.RESTRICT, related_name='applications')
    job = models.ForeignKey(JobPosting, on_delete=models.RESTRICT, related_name='applications')
    status = models.CharField(max_length=20, choices=ApplicationStatus.choices, default=ApplicationStatus.APPLIED)
    cover_letter = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"App: {self.student} -> {self.job.title} ({self.status})"
