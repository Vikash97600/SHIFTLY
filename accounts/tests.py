from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from students.models import StudentProfile
from businesses.models import BusinessProfile

User = get_user_model()

class AuthenticationTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.student_profile_url = reverse('student_profile')
        self.business_profile_url = reverse('business_profile')

        # Test registration payloads
        self.student_data = {
            "email": "student@shiftly.com",
            "password": "strongpassword123",
            "role": "student",
            "first_name": "John",
            "last_name": "Doe"
        }

        self.business_data = {
            "email": "business@shiftly.com",
            "password": "strongpassword123",
            "role": "business",
            "company_name": "Acme Corp"
        }

    def test_student_registration(self):
        """
        Verify that a student can register and a StudentProfile is created automatically.
        """
        response = self.client.post(self.register_url, self.student_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], self.student_data['email'])
        self.assertEqual(response.data['role'], 'student')
        
        # Check profile exists in DB
        user = User.objects.get(email=self.student_data['email'])
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())
        self.assertEqual(user.student_profile.first_name, "John")

    def test_business_registration(self):
        """
        Verify that a business owner can register and a BusinessProfile is created.
        """
        response = self.client.post(self.register_url, self.business_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['role'], 'business')
        
        # Check profile exists in DB
        user = User.objects.get(email=self.business_data['email'])
        self.assertTrue(BusinessProfile.objects.filter(user=user).exists())
        self.assertEqual(user.business_profile.company_name, "Acme Corp")

    def test_registration_validation(self):
        """
        Ensure required details are checked per role.
        """
        # Student registration missing first_name
        invalid_student = {
            "email": "student2@shiftly.com",
            "password": "strongpassword123",
            "role": "student"
        }
        response = self.client.post(self.register_url, invalid_student, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_and_jwt_payload(self):
        """
        Verify login generates tokens and returns proper custom user payload attributes.
        """
        # Register first
        self.client.post(self.register_url, self.student_data, format='json')
        
        # Login
        login_payload = {
            "email": self.student_data['email'],
            "password": self.student_data['password']
        }
        response = self.client.post(self.login_url, login_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['role'], 'student')
        self.assertEqual(response.data['email'], self.student_data['email'])

    def test_role_based_access_control(self):
        """
        Ensure students cannot access business profiles and vice versa.
        """
        # Create student and business users
        self.client.post(self.register_url, self.student_data, format='json')
        self.client.post(self.register_url, self.business_data, format='json')

        # Login student
        student_login = self.client.post(self.login_url, {
            "email": self.student_data['email'],
            "password": self.student_data['password']
        }, format='json')
        student_token = student_login.data['access']

        # Login business
        business_login = self.client.post(self.login_url, {
            "email": self.business_data['email'],
            "password": self.business_data['password']
        }, format='json')
        business_token = business_login.data['access']

        # 1. Student authenticating requests Student Profile -> Success
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {student_token}')
        response = self.client.get(self.student_profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 2. Student authenticating requests Business Profile -> Forbidden
        response = self.client.get(self.business_profile_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Business authenticating requests Business Profile -> Success
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {business_token}')
        response = self.client.get(self.business_profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 4. Business authenticating requests Student Profile -> Forbidden
        response = self.client.get(self.student_profile_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
