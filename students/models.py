from django.db import models
from django.conf import settings

class StudentProfile(models.Model):
    class Availability(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        BUSY = 'busy', 'Busy'
        UNAVAILABLE = 'unavailable', 'Unavailable'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    bio = models.TextField(blank=True, null=True)
    resume_url = models.URLField(max_length=255, blank=True, null=True)
    profile_picture_url = models.URLField(max_length=255, blank=True, null=True)
    reputation_score = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    hourly_rate_expectation = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    availability_status = models.CharField(max_length=20, choices=Availability.choices, default=Availability.AVAILABLE)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.category})"


class StudentSkill(models.Model):
    class Level(models.TextChoices):
        BEGINNER = 'beginner', 'Beginner'
        INTERMEDIATE = 'intermediate', 'Intermediate'
        ADVANCED = 'advanced', 'Advanced'

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='skills')
    skill = models.ForeignKey(Skill, on_delete=models.RESTRICT, related_name='students')
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.BEGINNER)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'skill')

    def __str__(self):
        return f"{self.student} - {self.skill.name} ({self.level})"
