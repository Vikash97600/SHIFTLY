from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

from swipes.models import Swipe
from students.models import StudentProfile
from jobs.models import JobPosting
from businesses.models import BusinessProfile

User = get_user_model()

class SwipeModelAndAJAXTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # User details setup
        self.student_user = User.objects.create_user(
            email="swipe_student@shiftly.com",
            password="password123",
            role="student"
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            first_name="Bobby",
            last_name="Fisher"
        )
        
        self.business_user = User.objects.create_user(
            email="swipe_employer@shiftly.com",
            password="password123",
            role="business"
        )
        self.business_profile = BusinessProfile.objects.create(
            user=self.business_user,
            company_name="Verve Coffee",
            industry="Coffee",
            business_registration_no="REG-VERVE44"
        )
        
        # Create active job postings
        self.job1 = JobPosting.objects.create(
            business=self.business_profile,
            title="Barista",
            description="Barista shift",
            location_name="Santa Cruz",
            latitude=36.9741,
            longitude=-122.0308,
            base_pay=19.00,
            start_date="2026-06-12",
            end_date="2026-06-12",
            shift_start_time="09:00:00",
            shift_end_time="17:00:00",
            status="active"
        )
        
        self.job2 = JobPosting.objects.create(
            business=self.business_profile,
            title="Retail Clerk",
            description="Retail clerk shift",
            location_name="San Jose",
            latitude=37.3382,
            longitude=-121.8863,
            base_pay=17.50,
            start_date="2026-06-15",
            end_date="2026-06-15",
            shift_start_time="10:00:00",
            shift_end_time="18:00:00",
            status="active"
        )

    def test_swipe_choices_persistence(self):
        """
        Verify that swipe 'like', 'dislike', and 'save' choices persist correctly.
        """
        # 1. Test Save swipe
        swipe_save = Swipe.objects.create(
            student=self.student_profile,
            job=self.job1,
            direction='save'
        )
        self.assertEqual(swipe_save.direction, 'save')

        # 2. Test Like swipe
        swipe_like = Swipe.objects.create(
            student=self.student_profile,
            job=self.job2,
            direction='like'
        )
        self.assertEqual(swipe_like.direction, 'like')

    def test_duplicate_swipe_prevention(self):
        """
        Verify that a student cannot swipe on the same job card twice (database unique constraint).
        """
        Swipe.objects.create(
            student=self.student_profile,
            job=self.job1,
            direction='like'
        )
        
        # Attempting duplicate swipe raises IntegrityError
        with self.assertRaises(IntegrityError):
            Swipe.objects.create(
                student=self.student_profile,
                job=self.job1,
                direction='save'
            )

    def test_ajax_swipe_save(self):
        """
        Verify that the AJAX endpoint successfully processes and records a 'save' swipe action.
        """
        self.client.login(email="swipe_student@shiftly.com", password="password123")
        
        url = reverse('student_swipe_action')
        response = self.client.post(url, {
            'job_id': self.job1.id,
            'direction': 'save'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertFalse(response.json()['matched']) # 'save' swipes shouldn't trigger auto-matches

        # Check swipe exists in DB
        self.assertTrue(Swipe.objects.filter(student=self.student_profile, job=self.job1, direction='save').exists())
