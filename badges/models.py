from django.db import models
from django.conf import settings
from students.models import StudentProfile

class SkillBadge(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    icon_url = models.URLField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class StudentBadge(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(SkillBadge, on_delete=models.RESTRICT, related_name='awarded_students')
    awarded_at = models.DateTimeField(auto_now_add=True)
    awarded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.RESTRICT, 
        related_name='badges_awarded'
    )

    class Meta:
        unique_together = ('student', 'badge')

    def __str__(self):
        return f"{self.student} has {self.badge.name}"
