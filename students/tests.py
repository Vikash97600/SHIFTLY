from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from .models import StudentProfile, Skill, StudentSkill, validate_file_size, validate_resume_extension, validate_portfolio_extension
from jobs.models import JobPosting
from swipes.models import Swipe
from matches.models import Match, JobApplication
from businesses.models import BusinessProfile

User = get_user_model()

class FileValidationTests(TestCase):
    def test_file_size_validation(self):
        """
        Verify files over 5MB raise validation errors.
        """
        large_file = SimpleUploadedFile("large_file.pdf", b"x" * (6 * 1024 * 1024)) # 6MB
        small_file = SimpleUploadedFile("small_file.pdf", b"x" * 1024) # 1KB
        
        with self.assertRaises(ValidationError):
            validate_file_size(large_file)
            
        try:
            validate_file_size(small_file)
        except ValidationError:
            self.fail("validate_file_size raised ValidationError unexpectedly!")

    def test_file_extension_validation(self):
        """
        Verify file extension restrictions.
        """
        invalid_resume = SimpleUploadedFile("resume.txt", b"my resume content")
        valid_resume = SimpleUploadedFile("resume.pdf", b"my resume content")
        
        with self.assertRaises(ValidationError):
            validate_resume_extension(invalid_resume)
            
        try:
            validate_resume_extension(valid_resume)
        except ValidationError:
            self.fail("validate_resume_extension raised ValidationError unexpectedly!")


class StudentViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # User roles setup
        self.student_user = User.objects.create_user(
            email="student@shiftly.com",
            password="password123",
            role="student"
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            first_name="Jane",
            last_name="Doe"
        )
        
        self.business_user = User.objects.create_user(
            email="business@shiftly.com",
            password="password123",
            role="business"
        )
        self.business_profile = BusinessProfile.objects.create(
            user=self.business_user,
            company_name="Cafe Nero",
            industry="Coffee",
            business_registration_no="REG-NERO12"
        )
        
        # Create active job post
        self.job = JobPosting.objects.create(
            business=self.business_profile,
            title="Barista Needed",
            description="Barista description",
            location_name="Downtown SF",
            latitude=37.7749,
            longitude=-122.4194,
            base_pay=18.50,
            start_date="2026-06-10",
            end_date="2026-06-10",
            shift_start_time="08:00:00",
            shift_end_time="16:00:00",
            status="active"
        )

    def test_dashboard_guards(self):
        """
        Ensure unauthenticated users and business owners are blocked from student dashboard.
        """
        url = reverse('student_dashboard')
        
        # 1. Unauthenticated -> redirects to login
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        
        # 2. Business user -> blocked (403 Forbidden)
        self.client.login(email="business@shiftly.com", password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        
        # 3. Student user -> success (200 OK)
        self.client.login(email="student@shiftly.com", password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_swiping_logic_and_matches(self):
        """
        Test that swiping 'like' creates a Swipe, and potentially a Match/Application.
        """
        self.client.login(email="student@shiftly.com", password="password123")
        
        # Swipe console loads active jobs
        url = reverse('student_swipe')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Barista Needed")

        # Perform 'like' swipe action via POST
        action_url = reverse('student_swipe_action')
        response = self.client.post(action_url, {
            'job_id': self.job.id,
            'direction': 'like'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        
        # Check that swipe was recorded
        self.assertTrue(Swipe.objects.filter(student=self.student_profile, job=self.job, direction='like').exists())
        
        # Check that match did NOT occur automatically (requires business owner acceptance)
        self.assertFalse(Match.objects.filter(student=self.student_profile, job=self.job).exists())
        self.assertTrue(JobApplication.objects.filter(student=self.student_profile, job=self.job).exists())
