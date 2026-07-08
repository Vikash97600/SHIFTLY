from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from students.models import StudentProfile
from businesses.models import BusinessProfile, Earning
from jobs.models import JobPosting
from matches.models import Match, JobApplication
from swipes.models import Swipe
from notifications.models import Notification

User = get_user_model()

class MatchEngineTests(APITestCase):
    def setUp(self):
        # 1. Create student user and profile
        self.student_user = User.objects.create_user(
            email="student_test@shiftly.com",
            password="password123",
            role="student"
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            first_name="Jane",
            last_name="Doe"
        )

        # 2. Create business user and profile
        self.business_user = User.objects.create_user(
            email="business_test@shiftly.com",
            password="password123",
            role="business",
            status=User.AccountStatus.APPROVED,
            is_active=True
        )
        self.business_profile = BusinessProfile.objects.create(
            user=self.business_user,
            company_name="Red Rocket",
            industry="Coffee",
            business_registration_no="REG-ROCKET12"
        )

        # 3. Create job posting
        self.job = JobPosting.objects.create(
            business=self.business_profile,
            title="Temp Barista",
            description="Short shift",
            location_name="San Francisco",
            latitude=37.7749,
            longitude=-122.4194,
            base_pay=20.00,
            start_date=timezone.now().date() + timezone.timedelta(days=2),
            end_date=timezone.now().date() + timezone.timedelta(days=2),
            shift_start_time="08:00:00",
            shift_end_time="16:00:00",
            status="active",
            slots_available=2
        )

        # 4. URLs
        self.swipe_action_url = reverse('student_swipe_action')
        self.hire_action_url = reverse('business_hire_action')
        self.match_api_list_url = reverse('match-list')

    def get_jwt_token(self, email, password):
        login_url = reverse('login')
        response = self.client.post(login_url, {"email": email, "password": password}, format='json')
        return response.data['access']

    def test_swipe_right_creates_no_match(self):
        """
        Verify that student swiping right (like) creates a Swipe and JobApplication,
        but does NOT automatically instantiate a Match.
        """
        # Login student using session
        self.client.login(email="student_test@shiftly.com", password="password123")

        # Perform swipe right
        response = self.client.post(self.swipe_action_url, {
            'job_id': self.job.id,
            'direction': 'like'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertFalse(response.json()['matched'])

        # Verify Swipe is created
        self.assertTrue(Swipe.objects.filter(student=self.student_profile, job=self.job, direction='like').exists())

        # Verify JobApplication is created with 'applied' status
        app_qs = JobApplication.objects.filter(student=self.student_profile, job=self.job)
        self.assertTrue(app_qs.exists())
        self.assertEqual(app_qs.first().status, 'applied')

        # Verify Match is NOT created
        self.assertFalse(Match.objects.filter(student=self.student_profile, job=self.job).exists())

    def test_business_hire_creates_match(self):
        """
        Verify that when a business owner accepts/hires the applicant:
        - The Match record is created.
        - The JobApplication status becomes 'accepted'.
        - Escrow ledger entry is logged.
        - Student receives a match notification.
        """
        # Setup application first (student applied)
        application = JobApplication.objects.create(
            student=self.student_profile,
            job=self.job,
            status='applied'
        )

        # Login business owner (employer uses session auth for dashboard views/actions)
        self.client.login(email="business_test@shiftly.com", password="password123")

        # Perform hire action
        response = self.client.post(self.hire_action_url, {
            'application_id': application.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        # Verify Match record is created
        match_qs = Match.objects.filter(student=self.student_profile, job=self.job)
        self.assertTrue(match_qs.exists())
        match = match_qs.first()
        self.assertEqual(match.status, 'hired')

        # Verify JobApplication links to Match and has 'accepted' status
        application.refresh_from_db()
        self.assertEqual(application.status, 'accepted')
        self.assertEqual(application.match, match)

        # Verify Escrow Earning ledger record
        self.assertTrue(Earning.objects.filter(student=self.student_profile, job=self.job, payment_status='escrow').exists())

        # Verify Notification sent to Student
        self.assertTrue(Notification.objects.filter(user=self.student_user, type='match').exists())

    def test_match_api_role_filtering(self):
        """
        Verify that the MatchViewSet lists matches filtered by the requesting user's role.
        """
        # Setup active match
        match = Match.objects.create(
            student=self.student_profile,
            job=self.job,
            status='active'
        )

        # 1. Student authenticating requests Match List
        student_token = self.get_jwt_token("student_test@shiftly.com", "password123")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {student_token}')

        response = self.client.get(self.match_api_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['job_title'], self.job.title)
        self.assertEqual(response.data[0]['company_name'], self.business_profile.company_name)

        # 2. Business authenticating requests Match List
        business_token = self.get_jwt_token("business_test@shiftly.com", "password123")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {business_token}')

        response = self.client.get(self.match_api_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['student_first_name'], self.student_profile.first_name)
        self.assertEqual(response.data[0]['student_last_name'], self.student_profile.last_name)

    def test_match_api_auth_required(self):
        """
        Verify unauthorized requests are rejected by MatchViewSet.
        """
        self.client.credentials()  # Clear credentials
        response = self.client.get(self.match_api_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
