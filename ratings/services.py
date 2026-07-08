import math
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from students.models import StudentProfile
from businesses.models import BusinessProfile, Earning
from matches.models import JobApplication, Match
from reports.models import Report
from jobs.models import JobPosting
from .models import (
    StudentReputation, StudentReputationHistory,
    BusinessReputation, BusinessReputationHistory,
    RatingReview
)

def recalculate_student_reputation(student_profile, reason="System Recalculation"):
    """
    Recalculates a student's reputation metrics and score, saves them to StudentReputation,
    logs a history entry, and updates student_profile.reputation_score.
    """
    with transaction.atomic():
        # Get or create the reputation record
        rep, _ = StudentReputation.objects.get_or_create(student=student_profile)
        
        # 1. Gather all accepted applications
        # Accepted/closed or withdrawn after acceptance
        accepted_apps = JobApplication.objects.filter(
            student=student_profile,
            status__in=['accepted', 'closed', 'withdrawn']
        )
        # Filter withdrawn applications to only those that actually had a Match (were accepted first)
        withdrawn_pre_hire = JobApplication.objects.filter(
            student=student_profile,
            status='withdrawn',
            match__isnull=True
        )
        accepted_apps = accepted_apps.exclude(id__in=withdrawn_pre_hire)
        accepted_count = accepted_apps.count()
        
        # Default safety fallbacks
        if accepted_count == 0:
            rep.attendance_rate = Decimal('100.00')
            rep.punctuality_rate = Decimal('100.00')
            rep.completion_rate = Decimal('100.00')
            rep.cancellation_rate = Decimal('0.00')
            rep.professional_score = Decimal('100.00')
            rep.average_rating = Decimal('5.00')
            rep.experience_bonus = 0
            rep.reputation_score = 100
            rep.save()
            
            # Log history
            StudentReputationHistory.objects.create(
                student=student_profile,
                reputation_score=100,
                attendance_rate=Decimal('100.00'),
                punctuality_rate=Decimal('100.00'),
                completion_rate=Decimal('100.00'),
                cancellation_rate=Decimal('0.00'),
                professional_score=Decimal('100.00'),
                average_rating=Decimal('5.00'),
                experience_bonus=0,
                change_reason=reason
            )
            
            student_profile.reputation_score = Decimal('100.00')
            student_profile.save()
            return rep

        # 2. Get reviews received by this student
        reviews = RatingReview.objects.filter(reviewee=student_profile.user)
        reviews_count = reviews.count()

        # Count attended shifts: all reviews except those marked absent
        attended_count = 0
        punctuality_scores = []
        rating_stars_sum = 0.0
        completed_count = 0
        professional_scores = []

        for r in reviews:
            cats = r.categories or {}
            is_absent = cats.get('attendance') == 'absent'
            
            if not is_absent:
                attended_count += 1
                
                # Punctuality
                punct = cats.get('punctuality', 'on_time')
                punct_map = {
                    'early': 100,
                    'on_time': 100,
                    'late_1_10': 70,
                    'late_10_20': 40,
                    'very_late': 0
                }
                punctuality_scores.append(punct_map.get(punct, 100))
                
                # Completed count (rated & closed)
                completed_count += 1
            
            # Overall Rating
            rating_stars_sum += float(r.rating)

            # Professional Behaviour
            prof_categories = ['communication', 'behaviour', 'teamwork', 'work_quality', 'professionalism']
            prof_vals = [float(cats.get(cat, 5)) for cat in prof_categories if cat in cats]
            if prof_vals:
                professional_scores.append(sum(prof_vals) / len(prof_vals))

        # Attendance Rate (25%)
        # Attendance Percentage = (Attended Shifts / Accepted Shifts) * 100
        attendance_rate = (Decimal(attended_count) / Decimal(accepted_count)) * 100
        attendance_comp = attendance_rate * Decimal('0.25')

        # Punctuality Rate (20%)
        # Average of punctuality scores
        if punctuality_scores:
            punctuality_rate = Decimal(sum(punctuality_scores) / len(punctuality_scores))
        else:
            punctuality_rate = Decimal('100.00')
        punctuality_comp = punctuality_rate * Decimal('0.20')

        # Employer Rating (20%)
        # Convert average rating to percentage
        if reviews_count > 0:
            avg_stars = Decimal(rating_stars_sum / reviews_count)
            rating_rate = (avg_stars / Decimal('5.00')) * 100
        else:
            avg_stars = Decimal('5.00')
            rating_rate = Decimal('100.00')
        rating_comp = rating_rate * Decimal('0.20')

        # Shift Completion (15%)
        # Completed Shifts / Accepted Shifts
        # Wait, completed shifts are those closed successfully (marked attended and rated/closed)
        completion_rate = (Decimal(completed_count) / Decimal(accepted_count)) * 100
        completion_comp = completion_rate * Decimal('0.15')

        # Cancellation Rate (10%)
        # Cancelled Shifts / Accepted Shifts
        # Cancelled Shifts = status withdrawn and match is not null
        cancelled_apps = accepted_apps.filter(status='withdrawn')
        cancelled_count = cancelled_apps.count()
        cancellation_rate = (Decimal(cancelled_count) / Decimal(accepted_count)) * 100
        cancellation_comp = (Decimal('100.00') - cancellation_rate) * Decimal('0.10')

        # Professional Behaviour (5%)
        # Convert average score (1-5) to percentage
        if professional_scores:
            avg_prof = Decimal(sum(professional_scores) / len(professional_scores))
            professional_rate = (avg_prof / Decimal('5.00')) * 100
        else:
            avg_prof = Decimal('5.00')
            professional_rate = Decimal('100.00')
        professional_comp = professional_rate * Decimal('0.05')

        # Experience Bonus (5%)
        # Completed counts
        if completed_count >= 200:
            bonus = 5
        elif completed_count >= 100:
            bonus = 4
        elif completed_count >= 50:
            bonus = 3
        elif completed_count >= 25:
            bonus = 2
        elif completed_count >= 10:
            bonus = 1
        else:
            bonus = 0

        # Sum and round
        final_score = int(round(
            float(attendance_comp) +
            float(punctuality_comp) +
            float(rating_comp) +
            float(completion_comp) +
            float(cancellation_comp) +
            float(professional_comp) +
            float(bonus)
        ))
        final_score = max(0, min(100, final_score))

        # Save updates
        rep.attendance_rate = attendance_rate
        rep.punctuality_rate = punctuality_rate
        rep.completion_rate = completion_rate
        rep.cancellation_rate = cancellation_rate
        rep.professional_score = professional_rate
        rep.average_rating = avg_stars
        rep.experience_bonus = bonus
        rep.reputation_score = final_score
        rep.save()

        # Log history
        StudentReputationHistory.objects.create(
            student=student_profile,
            reputation_score=final_score,
            attendance_rate=attendance_rate,
            punctuality_rate=punctuality_rate,
            completion_rate=completion_rate,
            cancellation_rate=cancellation_rate,
            professional_score=professional_rate,
            average_rating=avg_stars,
            experience_bonus=bonus,
            change_reason=reason
        )

        student_profile.reputation_score = Decimal(final_score)
        student_profile.save()
        return rep


def recalculate_business_reputation(business_profile, reason="System Recalculation"):
    """
    Recalculates a business's reputation metrics and score, saves them to BusinessReputation,
    logs a history entry, and updates business_profile.reputation_score.
    """
    with transaction.atomic():
        rep, _ = BusinessReputation.objects.get_or_create(business=business_profile)
        
        # 1. Total Jobs Posted
        posted_jobs = JobPosting.objects.filter(business=business_profile)
        total_jobs_count = posted_jobs.count()

        # 2. Get reviews received by this business (reviews given by students)
        reviews = RatingReview.objects.filter(reviewee=business_profile.user)
        reviews_count = reviews.count()

        # Default fallback
        if total_jobs_count == 0:
            rep.average_rating = Decimal('5.00')
            rep.payment_timeliness_rate = Decimal('100.00')
            rep.job_accuracy_rate = Decimal('100.00')
            rep.cancellation_rate = Decimal('0.00')
            rep.complaint_resolution_rate = Decimal('100.00')
            rep.reputation_score = 100
            rep.save()

            BusinessReputationHistory.objects.create(
                business=business_profile,
                reputation_score=100,
                average_rating=Decimal('5.00'),
                payment_timeliness_rate=Decimal('100.00'),
                job_accuracy_rate=Decimal('100.00'),
                cancellation_rate=Decimal('0.00'),
                complaint_resolution_rate=Decimal('100.00'),
                change_reason=reason
            )

            business_profile.reputation_score = Decimal('100.00')
            business_profile.save()
            return rep

        # Student Ratings (30%)
        rating_stars_sum = 0.0
        accuracy_stars_sum = 0.0
        accuracy_count = 0
        timeliness_scores = []

        for r in reviews:
            rating_stars_sum += float(r.rating)
            cats = r.categories or {}
            
            # Job Accuracy (1-5 stars)
            acc = cats.get('job_accuracy')
            if acc is not None:
                accuracy_stars_sum += float(acc)
                accuracy_count += 1

            # Payment timeliness speed calculation
            # Try to find payment release delta
            match = r.match
            if match and match.job:
                # Combining Date and Time fields to aware datetime
                job = match.job
                try:
                    naive_end = datetime.combine(job.end_date, job.shift_end_time)
                    shift_end_dt = timezone.make_aware(naive_end)
                    diff_hours = (r.created_at - shift_end_dt).total_seconds() / 3600.0
                    
                    if diff_hours <= 12:
                        score = 100
                    elif diff_hours <= 24:
                        score = 80
                    elif diff_hours <= 48:
                        score = 60
                    elif diff_hours <= 72:
                        score = 40
                    else:
                        score = 0
                    timeliness_scores.append(score)
                except Exception:
                    pass

        # Rating component
        if reviews_count > 0:
            avg_stars = Decimal(rating_stars_sum / reviews_count)
            rating_rate = (avg_stars / Decimal('5.00')) * 100
        else:
            avg_stars = Decimal('5.00')
            rating_rate = Decimal('100.00')
        rating_comp = rating_rate * Decimal('0.30')

        # Payment Timeliness (25%)
        if timeliness_scores:
            timeliness_rate = Decimal(sum(timeliness_scores) / len(timeliness_scores))
        else:
            timeliness_rate = Decimal('100.00')
        timeliness_comp = timeliness_rate * Decimal('0.25')

        # Job Accuracy (20%)
        if accuracy_count > 0:
            avg_acc = Decimal(accuracy_stars_sum / accuracy_count)
            accuracy_rate = (avg_acc / Decimal('5.00')) * 100
        else:
            avg_acc = Decimal('5.00')
            accuracy_rate = Decimal('100.00')
        accuracy_comp = accuracy_rate * Decimal('0.20')

        # Shift Cancellation (15%)
        cancelled_jobs = posted_jobs.filter(status='cancelled')
        cancelled_count = cancelled_jobs.count()
        cancellation_rate = (Decimal(cancelled_count) / Decimal(total_jobs_count)) * 100
        cancellation_comp = (Decimal('100.00') - cancellation_rate) * Decimal('0.15')

        # Complaint Resolution (10%)
        complaints = Report.objects.filter(reported_user=business_profile.user)
        complaints_count = complaints.count()
        if complaints_count > 0:
            resolved_complaints = complaints.filter(status__in=['resolved', 'dismissed']).count()
            complaint_rate = (Decimal(resolved_complaints) / Decimal(complaints_count)) * 100
        else:
            complaint_rate = Decimal('100.00')
        complaint_comp = complaint_rate * Decimal('0.10')

        # Sum and round
        final_score = int(round(
            float(rating_comp) +
            float(timeliness_comp) +
            float(accuracy_comp) +
            float(cancellation_comp) +
            float(complaint_comp)
        ))
        final_score = max(0, min(100, final_score))

        # Save updates
        rep.average_rating = avg_stars
        rep.payment_timeliness_rate = timeliness_rate
        rep.job_accuracy_rate = accuracy_rate
        rep.cancellation_rate = cancellation_rate
        rep.complaint_resolution_rate = complaint_rate
        rep.reputation_score = final_score
        rep.save()

        # Log history
        BusinessReputationHistory.objects.create(
            business=business_profile,
            reputation_score=final_score,
            average_rating=avg_stars,
            payment_timeliness_rate=timeliness_rate,
            job_accuracy_rate=accuracy_rate,
            cancellation_rate=cancellation_rate,
            complaint_resolution_rate=complaint_rate,
            change_reason=reason
        )

        business_profile.reputation_score = Decimal(final_score)
        business_profile.save()
        return rep
