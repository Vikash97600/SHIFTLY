from django.db.models.signals import post_save
from django.dispatch import receiver
from ratings.models import RatingReview
from matches.models import JobApplication
from jobs.models import JobPosting
from reports.models import Report
from students.models import StudentProfile
from businesses.models import BusinessProfile
from ratings.services import recalculate_student_reputation, recalculate_business_reputation

@receiver(post_save, sender=RatingReview)
def handle_rating_review_save(sender, instance, created, **kwargs):
    """
    Recalculates reputation of the reviewee whenever a rating is submitted.
    """
    reviewee = instance.reviewee
    if reviewee.role == 'student':
        try:
            profile = StudentProfile.objects.get(user=reviewee)
            recalculate_student_reputation(profile, reason="Rating submitted by employer")
        except StudentProfile.DoesNotExist:
            pass
    elif reviewee.role == 'business':
        try:
            profile = BusinessProfile.objects.get(user=reviewee)
            recalculate_business_reputation(profile, reason="Rating submitted by student")
        except BusinessProfile.DoesNotExist:
            pass

@receiver(post_save, sender=JobApplication)
def handle_job_application_save(sender, instance, created, **kwargs):
    """
    Recalculates reputation of the student whenever application status changes (e.g. accepted, withdrawn, closed).
    """
    profile = instance.student
    recalculate_student_reputation(profile, reason=f"Application status updated to {instance.status}")

@receiver(post_save, sender=JobPosting)
def handle_job_posting_save(sender, instance, created, **kwargs):
    """
    Recalculates reputation of the business owner if job posting status changes (e.g. cancelled).
    """
    profile = instance.business
    recalculate_business_reputation(profile, reason=f"Shift posting status updated to {instance.status}")

@receiver(post_save, sender=Report)
def handle_report_save(sender, instance, created, **kwargs):
    """
    Recalculates reputation of the reported user when resolution status changes.
    """
    reported_user = instance.reported_user
    if not reported_user:
        return
        
    if reported_user.role == 'student':
        try:
            profile = StudentProfile.objects.get(user=reported_user)
            recalculate_student_reputation(profile, reason=f"Complaint status updated to {instance.status}")
        except StudentProfile.DoesNotExist:
            pass
    elif reported_user.role == 'business':
        try:
            profile = BusinessProfile.objects.get(user=reported_user)
            recalculate_business_reputation(profile, reason=f"Complaint status updated to {instance.status}")
        except BusinessProfile.DoesNotExist:
            pass
