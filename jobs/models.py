import uuid
from django.db import models
from businesses.models import BusinessProfile
from students.models import Skill

class JobPosting(models.Model):
    class WorkType(models.TextChoices):
        REMOTE = 'remote', 'Remote'
        HYBRID = 'hybrid', 'Hybrid'
        ONSITE = 'onsite', 'Onsite'

    class RateType(models.TextChoices):
        HOURLY = 'hourly', 'Hourly'
        FIXED = 'fixed', 'Fixed'

    class JobStatus(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        FILLED = 'filled', 'Filled'
        ARCHIVED = 'archived', 'Archived'
        CANCELLED = 'cancelled', 'Cancelled'

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    business = models.ForeignKey(BusinessProfile, on_delete=models.RESTRICT, related_name='jobs')
    title = models.CharField(max_length=255)
    description = models.TextField()
    work_type = models.CharField(max_length=20, choices=WorkType.choices, default=WorkType.ONSITE)
    location_name = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    base_pay = models.DecimalField(max_digits=10, decimal_places=2)
    rate_type = models.CharField(max_length=20, choices=RateType.choices, default=RateType.HOURLY)
    start_date = models.DateField()
    end_date = models.DateField()
    shift_start_time = models.TimeField()
    shift_end_time = models.TimeField()
    slots_available = models.PositiveIntegerField(default=1)
    slots_filled = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} at {self.business.company_name}"


class JobRequiredSkill(models.Model):
    class Priority(models.TextChoices):
        REQUIRED = 'required', 'Required'
        PREFERRED = 'preferred', 'Preferred'

    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='required_skills')
    skill = models.ForeignKey(Skill, on_delete=models.RESTRICT, related_name='jobs_requiring')
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.REQUIRED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('job', 'skill')

    def __str__(self):
        return f"{self.job.title} requires {self.skill.name} ({self.priority})"
