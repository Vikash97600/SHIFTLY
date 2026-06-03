from django.db import models
from django.conf import settings
from jobs.models import JobPosting

class Report(models.Model):
    class ReportStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        INVESTIGATING = 'investigating', 'Investigating'
        RESOLVED = 'resolved', 'Resolved'
        DISMISSED = 'dismissed', 'Dismissed'

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_submitted')
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reports_received'
    )
    reported_job = models.ForeignKey(
        JobPosting, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reports_received'
    )
    reason_category = models.CharField(max_length=50)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=ReportStatus.choices, default=ReportStatus.PENDING)
    resolver = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='resolved_reports'
    )
    resolution_action = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Report {self.id} status: {self.status}"
