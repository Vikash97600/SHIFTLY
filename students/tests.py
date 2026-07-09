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
            last_name="Doe",
            latitude=37.7749,
            longitude=-122.4194
        )
        
        self.business_user = User.objects.create_user(
            email="business@shiftly.com",
            password="password123",
            role="business",
            status=User.AccountStatus.APPROVED,
            is_active=True
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


class DynamicHiringRadiusTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student_user = User.objects.create_user(
            email="jane@shiftly.com",
            password="password123",
            role="student"
        )
        # Jane is in Bangalore, India (12.9716, 77.5946)
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            first_name="Jane",
            last_name="Doe",
            latitude=12.9716,
            longitude=77.5946
        )
        
        self.business_user = User.objects.create_user(
            email="business@shiftly.com",
            password="password123",
            role="business",
            status=User.AccountStatus.APPROVED,
            is_active=True
        )
        self.business_profile = BusinessProfile.objects.create(
            user=self.business_user,
            company_name="Bangalore Brews",
            industry="Coffee",
            business_registration_no="REG-BREWS12"
        )
        
        # 1. On-site Job A: distance ~0.9 km (visible, radius = 3 km)
        self.job_a = JobPosting.objects.create(
            business=self.business_profile,
            title="Job A - Close Onsite",
            description="Nearby cafe onsite shift",
            location_name="MG Road",
            latitude=12.9800,
            longitude=77.5946,
            base_pay=18.50,
            start_date="2026-06-10",
            end_date="2026-06-10",
            shift_start_time="08:00:00",
            shift_end_time="16:00:00",
            status="active",
            job_mode="onsite",
            hiring_radius=3.00,
            category="cafe_restaurant"
        )

        # 2. On-site Job B: distance ~5.7 km (hidden, radius = 3 km)
        self.job_b = JobPosting.objects.create(
            business=self.business_profile,
            title="Job B - Far Onsite Small Radius",
            description="Far Cafe onsite shift",
            location_name="Jayanagar",
            latitude=12.9200,
            longitude=77.5946,
            base_pay=20.00,
            start_date="2026-06-10",
            end_date="2026-06-10",
            shift_start_time="08:00:00",
            shift_end_time="16:00:00",
            status="active",
            job_mode="onsite",
            hiring_radius=3.00,
            category="cafe_restaurant"
        )

        # 3. On-site Job C: distance ~5.7 km (visible, radius = 10 km)
        self.job_c = JobPosting.objects.create(
            business=self.business_profile,
            title="Job C - Far Onsite Large Radius",
            description="Far Cafe onsite shift with large radius",
            location_name="Jayanagar Large Radius",
            latitude=12.9200,
            longitude=77.5946,
            base_pay=22.00,
            start_date="2026-06-10",
            end_date="2026-06-10",
            shift_start_time="08:00:00",
            shift_end_time="16:00:00",
            status="active",
            job_mode="onsite",
            hiring_radius=10.00,
            category="cafe_restaurant"
        )

        # 4. Remote Job D: distance ignored (always visible)
        self.job_d = JobPosting.objects.create(
            business=self.business_profile,
            title="Job D - Remote",
            description="Remote coding work",
            location_name="Remote",
            latitude=0.0,
            longitude=0.0,
            base_pay=25.00,
            start_date="2026-06-10",
            end_date="2026-06-10",
            shift_start_time="08:00:00",
            shift_end_time="16:00:00",
            status="active",
            job_mode="remote",
            hiring_radius=999.00,
            category="software_developer",
            is_urgent=True
        )

    def test_geospatial_visibility_rules(self):
        from students.views import get_visible_jobs_for_student
        
        # Call the visibility helper with no extra search filters
        visible_jobs = get_visible_jobs_for_student(self.student_profile, {})
        visible_ids = list(visible_jobs.values_list('id', flat=True))

        # Job A (Close) -> True
        self.assertIn(self.job_a.id, visible_ids)
        # Job B (Far, small radius) -> False
        self.assertNotIn(self.job_b.id, visible_ids)
        # Job C (Far, large radius) -> True
        self.assertIn(self.job_c.id, visible_ids)
        # Job D (Remote) -> True
        self.assertIn(self.job_d.id, visible_ids)

    def test_search_filters(self):
        from students.views import get_visible_jobs_for_student

        # Test Remote Only Filter
        visible_jobs = get_visible_jobs_for_student(self.student_profile, {'remote_only': 'true'})
        self.assertEqual(visible_jobs.count(), 1)
        self.assertEqual(visible_jobs.first().id, self.job_d.id)

        # Test Radius Limit Filter (within 2km, should hide Job C even though its radius is 10km)
        visible_jobs = get_visible_jobs_for_student(self.student_profile, {'radius': '2.00'})
        visible_ids = list(visible_jobs.values_list('id', flat=True))
        self.assertIn(self.job_a.id, visible_ids)
        self.assertNotIn(self.job_c.id, visible_ids)

        # Test Urgent Filter
        visible_jobs = get_visible_jobs_for_student(self.student_profile, {'urgent': 'true'})
        self.assertEqual(visible_jobs.count(), 1)
        self.assertEqual(visible_jobs.first().id, self.job_d.id)

