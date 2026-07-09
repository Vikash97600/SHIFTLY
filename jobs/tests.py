from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from businesses.models import BusinessProfile
from students.models import StudentProfile
from matches.models import JobApplication
from .models import JobPosting

User = get_user_model()

class JobEditDeleteTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create Business Owner A
        self.biz_user_a = User.objects.create_user(
            email="biz_a@shiftly.com",
            password="password123",
            role="business",
            status=User.AccountStatus.APPROVED,
            is_active=True
        )
        self.biz_profile_a = BusinessProfile.objects.create(
            user=self.biz_user_a,
            company_name="Cafe Alpha",
            industry="Coffee",
            business_registration_no="REG-ALPHA12"
        )
        
        # Create Business Owner B
        self.biz_user_b = User.objects.create_user(
            email="biz_b@shiftly.com",
            password="password123",
            role="business",
            status=User.AccountStatus.APPROVED,
            is_active=True
        )
        self.biz_profile_b = BusinessProfile.objects.create(
            user=self.biz_user_b,
            company_name="Cafe Beta",
            industry="Coffee",
            business_registration_no="REG-BETA12"
        )
        
        # Create Student
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

        # Create Job A (belonging to Business A)
        self.job_a = JobPosting.objects.create(
            business=self.biz_profile_a,
            title="Barista Alpha",
            description="Barista description",
            location_name="Downtown SF",
            latitude=37.7749,
            longitude=-122.4194,
            base_pay=18.50,
            start_date="2026-08-10",
            end_date="2026-08-10",
            shift_start_time="08:00:00",
            shift_end_time="16:00:00",
            status="active",
            job_mode="onsite",
            hiring_radius=4.00,
            category="cafe_restaurant"
        )

    def test_edit_job_success(self):
        """
        Verify a business owner can edit their own shift.
        """
        self.client.login(email="biz_a@shiftly.com", password="password123")
        
        url = reverse('job_edit', args=[self.job_a.id])
        
        # GET request to load edit page
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # POST request to save changes
        data = {
            'title': "Specialty Barista",
            'description': "Updated description",
            'category': 'cafe_restaurant',
            'job_mode': 'onsite',
            'hiring_radius': '5.00',
            'base_pay': '22.00',
            'location_name': "Downtown SF",
            'latitude': '37.7749',
            'longitude': '-122.4194',
            'start_date': "2026-08-10",
            'end_date': "2026-08-10",
            'shift_start_time': "09:00:00",
            'shift_end_time': "17:00:00",
            'slots_available': 3,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # Redirect to manage page
        
        # Assert database updated
        self.job_a.refresh_from_db()
        self.assertEqual(self.job_a.title, "Specialty Barista")
        self.assertEqual(self.job_a.base_pay, 22.00)
        self.assertEqual(self.job_a.hiring_radius, 5.00)

    def test_edit_job_unauthorized(self):
        """
        Verify a business owner cannot edit another business's shift.
        """
        # Login as Business B
        self.client.login(email="biz_b@shiftly.com", password="password123")
        
        url = reverse('job_edit', args=[self.job_a.id])
        
        # Should return 404 since it filters by self.biz_profile_b
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        
        response = self.client.post(url, {'title': "Attempted Hack"})
        self.assertEqual(response.status_code, 404)

    def test_delete_job_success(self):
        """
        Verify a business owner can delete a shift with no associated active applications/matches.
        """
        self.client.login(email="biz_a@shiftly.com", password="password123")
        
        url = reverse('job_delete', args=[self.job_a.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        # Verify job is deleted
        self.assertFalse(JobPosting.objects.filter(id=self.job_a.id).exists())

    def test_delete_job_safety_restriction(self):
        """
        Verify that a job cannot be deleted if there is a student application referencing it.
        """
        # Create an application for Job A
        JobApplication.objects.create(
            student=self.student_profile,
            job=self.job_a,
            status='applied'
        )
        
        self.client.login(email="biz_a@shiftly.com", password="password123")
        
        url = reverse('job_delete', args=[self.job_a.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        # Verify job was NOT deleted because of models.RESTRICT
        self.assertTrue(JobPosting.objects.filter(id=self.job_a.id).exists())
        
        # Verify warning message was added
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("cannot be deleted because there are active applications", messages[0].message)

    def test_delete_job_unauthorized(self):
        """
        Verify a business owner cannot delete another business's shift.
        """
        # Login as Business B
        self.client.login(email="biz_b@shiftly.com", password="password123")
        
        url = reverse('job_delete', args=[self.job_a.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(JobPosting.objects.filter(id=self.job_a.id).exists())
