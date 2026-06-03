from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from businesses.models import BusinessProfile, Earning
from students.models import StudentProfile
from jobs.models import JobPosting
from matches.models import Match, JobApplication
from notifications.models import Notification
from ratings.models import RatingReview

User = get_user_model()

class BusinessModuleTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Employer Setup
        self.business_user = User.objects.create_user(
            email="employer@shiftly.com",
            password="password123",
            role="business"
        )
        self.business_profile = BusinessProfile.objects.create(
            user=self.business_user,
            company_name="Cafe Rosso",
            industry="Coffee",
            business_registration_no="REG-ROSSO12"
        )
        
        # Student Setup
        self.student_user = User.objects.create_user(
            email="student@shiftly.com",
            password="password123",
            role="student"
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            first_name="Alice",
            last_name="Smith"
        )
        
        # Job Setup (Draft to make it active in views test)
        self.job = JobPosting.objects.create(
            business=self.business_profile,
            title="Specialty Barista",
            description="Barista shift at Cafe Rosso",
            location_name="North Beach, SF",
            latitude=37.7994,
            longitude=-122.4082,
            base_pay=20.00,
            start_date=timezone.now().date() + timezone.timedelta(days=1),
            end_date=timezone.now().date() + timezone.timedelta(days=1),
            shift_start_time="08:00:00",
            shift_end_time="16:00:00",
            slots_available=1,
            status="active"
        )

        # Match & Application Setup
        self.match = Match.objects.create(
            student=self.student_profile,
            job=self.job,
            status="active"
        )
        self.application = JobApplication.objects.create(
            match=self.match,
            student=self.student_profile,
            job=self.job,
            status="applied"
        )

    def test_dashboard_guards(self):
        """
        Verify that student user is blocked (403) from accessing the business dashboard.
        """
        url = reverse('business_dashboard')
        
        # 1. Accessing as student -> Blocked (403)
        self.client.login(email="student@shiftly.com", password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # 2. Accessing as business owner -> Success (200 OK)
        self.client.login(email="employer@shiftly.com", password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_job_posting_limits(self):
        """
        Test validator constraints when creating job postings via POST.
        """
        self.client.login(email="employer@shiftly.com", password="password123")
        
        url = reverse('job_post')
        
        # 1. Invalid date (in the past)
        payload = {
            'title': 'New Barista Shift',
            'description': 'description of shift',
            'work_type': 'onsite',
            'location_name': 'SF',
            'latitude': 37.77,
            'longitude': -122.41,
            'base_pay': 18.00,
            'rate_type': 'hourly',
            'start_date': timezone.now().date() - timezone.timedelta(days=1), # Yesterday
            'end_date': timezone.now().date(),
            'shift_start_time': '09:00',
            'shift_end_time': '17:00',
            'slots_available': 1
        }
        response = self.client.post(url, payload)
        self.assertFormError(response, 'form', 'start_date', "Start date cannot be in the past.")

    def test_hiring_action_locks_escrow(self):
        """
        Verify the hiring AJAX handler updates statuses and logs escrow payments.
        """
        self.client.login(email="employer@shiftly.com", password="password123")
        
        url = reverse('business_hire_action')
        response = self.client.post(url, {
            'application_id': self.application.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        
        # Check that statuses are updated
        self.application.refresh_from_db()
        self.match.refresh_from_db()
        self.assertEqual(self.application.status, 'accepted')
        self.assertEqual(self.match.status, 'hired')
        
        # Verify escrow record was instantiated in database
        earning = Earning.objects.get(student=self.student_profile, job=self.job)
        self.assertEqual(earning.payment_status, 'escrow')
        # 8 hours shift @ $20 = $160 gross. 10% fee = $16. Net = $144.
        self.assertEqual(earning.net_amount, Decimal('144.00'))

        # Verify notification was sent to student
        self.assertTrue(Notification.objects.filter(user=self.student_user, type='payment').exists())

    def test_rating_student_releases_escrow(self):
        """
        Test that rating a student releases payouts from escrow and updates reputation score.
        """
        # Lock escrow first by simulating hire
        self.client.login(email="employer@shiftly.com", password="password123")
        self.client.post(reverse('business_hire_action'), {
            'application_id': self.application.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Submit a rating
        rating_url = reverse('business_rate_student', args=[self.application.id])
        response = self.client.post(rating_url, {
            'rating': '5.0',
            'feedback_text': 'Exceeded expectations. Very professional!'
        })
        
        self.assertEqual(response.status_code, 302) # Redirects on success
        
        # Verify earning status released
        earning = Earning.objects.get(student=self.student_profile, job=self.job)
        self.assertEqual(earning.payment_status, 'released')

        # Verify student reputation score updated (5.0 rating * 20 = 100 reputation score)
        self.student_profile.refresh_from_db()
        self.assertEqual(self.student_profile.reputation_score, Decimal('100.00'))
