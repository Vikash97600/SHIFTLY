from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from students.models import StudentProfile
from businesses.models import BusinessProfile
from jobs.models import JobPosting
from matches.models import Match, JobApplication
from ratings.models import RatingReview, StudentReputation, BusinessReputation
from ratings.services import recalculate_student_reputation, recalculate_business_reputation
import datetime

User = get_user_model()


def make_student_user(email='student@test.com', password='pass1234!'):
    user = User.objects.create_user(
        email=email, password=password,
        role='student', status='approved', is_active=True
    )
    profile = StudentProfile.objects.create(
        user=user, first_name='Test', last_name='Student'
    )
    return user, profile


def make_business_user(email='biz@test.com', password='pass1234!'):
    user = User.objects.create_user(
        email=email, password=password,
        role='business', status='approved', is_active=True
    )
    profile = BusinessProfile.objects.create(
        user=user, company_name='Test Corp',
        industry='Retail', business_registration_no='REG-TEST-001'
    )
    return user, profile


def make_job(business, **kwargs):
    defaults = dict(
        title='Test Shift',
        description='A test shift description',
        location_name='Test City',
        latitude='12.9716',
        longitude='77.5946',
        base_pay=Decimal('500.00'),
        start_date=datetime.date.today(),
        end_date=datetime.date.today(),
        shift_start_time=datetime.time(9, 0),
        shift_end_time=datetime.time(17, 0),
        slots_available=3,
        work_type='on-site',
        status='active',
    )
    defaults.update(kwargs)
    return JobPosting.objects.create(business=business, **defaults)


class StudentReputationDefaultTest(TestCase):
    """A new student with no accepted applications should default to 100."""

    def setUp(self):
        self.user, self.profile = make_student_user()

    def test_default_score_100(self):
        rep = recalculate_student_reputation(self.profile, reason='Initial')
        self.assertEqual(rep.reputation_score, 100)
        self.assertEqual(rep.attendance_rate, Decimal('100.00'))
        self.assertEqual(rep.cancellation_rate, Decimal('0.00'))


class StudentReputationWithReviewTest(TestCase):
    """A student who completed a shift and received a perfect review should keep near-100 score."""

    def setUp(self):
        self.s_user, self.s_profile = make_student_user()
        self.b_user, self.b_profile = make_business_user()
        self.job = make_job(self.b_profile)

        # Create accepted match and closed application
        self.match = Match.objects.create(
            student=self.s_profile, job=self.job, status='hired'
        )
        self.app = JobApplication.objects.create(
            match=self.match, student=self.s_profile, job=self.job, status='closed'
        )

        # Employer gives perfect rating
        RatingReview.objects.create(
            match=self.match,
            reviewer=self.b_user,
            reviewee=self.s_user,
            rating=Decimal('5.0'),
            categories={
                'attendance': 'present',
                'punctuality': 'on_time',
                'communication': 5,
                'behaviour': 5,
                'teamwork': 5,
                'work_quality': 5,
                'professionalism': 5,
            }
        )

    def test_high_score_with_perfect_review(self):
        rep = recalculate_student_reputation(self.s_profile, reason='Post-shift')
        self.assertGreaterEqual(rep.reputation_score, 95)
        self.assertEqual(rep.average_rating, Decimal('5.0'))

    def test_reputation_history_created(self):
        from ratings.models import StudentReputationHistory
        recalculate_student_reputation(self.s_profile, reason='Post-shift')
        history_count = StudentReputationHistory.objects.filter(student=self.s_profile).count()
        self.assertGreaterEqual(history_count, 1)


class StudentCancellationPenaltyTest(TestCase):
    """A student who withdrew after being hired should receive a cancellation penalty."""

    def setUp(self):
        self.s_user, self.s_profile = make_student_user()
        self.b_user, self.b_profile = make_business_user()
        self.job = make_job(self.b_profile)

        self.match = Match.objects.create(
            student=self.s_profile, job=self.job, status='active'
        )
        # Accepted then withdrawn (cancellation after hire)
        self.app = JobApplication.objects.create(
            match=self.match, student=self.s_profile, job=self.job, status='withdrawn'
        )

    def test_cancellation_reduces_score(self):
        # No reviews, one cancelled shift
        rep = recalculate_student_reputation(self.s_profile, reason='Cancellation test')
        self.assertLess(rep.reputation_score, 100)


class BusinessReputationDefaultTest(TestCase):
    """A new business with no jobs should default to 100."""

    def setUp(self):
        self.b_user, self.b_profile = make_business_user()

    def test_default_score_100(self):
        rep = recalculate_business_reputation(self.b_profile, reason='Initial')
        self.assertEqual(rep.reputation_score, 100)
        self.assertEqual(rep.payment_timeliness_rate, Decimal('100.00'))
        self.assertEqual(rep.cancellation_rate, Decimal('0.00'))


class BusinessCancellationPenaltyTest(TestCase):
    """A business that cancels jobs should have a lower reputation."""

    def setUp(self):
        self.b_user, self.b_profile = make_business_user()
        self.job1 = make_job(self.b_profile, title='Job 1')
        self.job2 = make_job(self.b_profile, title='Job 2 Cancelled', status='cancelled')

    def test_cancellation_reduces_score(self):
        rep = recalculate_business_reputation(self.b_profile, reason='Cancellation test')
        # 1 cancelled out of 2 jobs = 50% cancellation rate — should be > 0
        self.assertGreater(rep.cancellation_rate, Decimal('0.00'))
        self.assertLess(rep.reputation_score, 100)

    def test_business_reputation_history_created(self):
        from ratings.models import BusinessReputationHistory
        recalculate_business_reputation(self.b_profile, reason='Cancellation test')
        history_count = BusinessReputationHistory.objects.filter(business=self.b_profile).count()
        self.assertGreaterEqual(history_count, 1)
