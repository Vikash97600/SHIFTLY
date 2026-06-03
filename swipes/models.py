from django.db import models
from students.models import StudentProfile
from jobs.models import JobPosting

class Swipe(models.Model):
    class Direction(models.TextChoices):
        LIKE = 'like', 'Like'
        DISLIKE = 'dislike', 'Dislike'

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='swipes')
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='swipes')
    direction = models.CharField(max_length=10, choices=Direction.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'job')

    def __str__(self):
        return f"{self.student} swiped {self.direction} on {self.job.title}"
