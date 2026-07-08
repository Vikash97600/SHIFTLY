from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from students.models import StudentProfile
from businesses.models import BusinessProfile
from notifications.models import Notification

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

    def test_admin_registration_is_blocked(self):
        """
        Public registration must never create an admin user.
        """
        response = self.client.post(self.register_url, {
            "email": "admin@shiftly.com",
            "password": "strongpassword123",
            "role": "admin"
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="admin@shiftly.com").exists())

    def test_pending_business_cannot_login(self):
        """
        Business accounts should stay pending until an admin approves them.
        """
        self.client.post(self.register_url, self.business_data, format='json')
        business_user = User.objects.get(email=self.business_data['email'])

        self.assertEqual(business_user.status, User.AccountStatus.PENDING)
        self.assertFalse(business_user.is_active)

        login_response = self.client.post(self.login_url, {
            "email": self.business_data['email'],
            "password": self.business_data['password']
        }, format='json')

        self.assertEqual(login_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(Notification.objects.filter(user=business_user).exists())

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

        # Approve the business user before allowing login
        business_user = User.objects.get(email=self.business_data['email'])
        business_user.status = User.AccountStatus.APPROVED
        business_user.is_active = True
        business_user.save(update_fields=['status', 'is_active'])

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


from django.test import TestCase, Client
from django.urls import reverse

class HTMLAuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_model = get_user_model()

    def test_landing_page_loads(self):
        response = self.client.get(reverse('landing'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing.html')

    def test_login_page_loads(self):
        response = self.client.get(reverse('login_page'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_register_page_loads(self):
        response = self.client.get(reverse('register_page'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')

    def test_about_page_loads(self):
        response = self.client.get(reverse('about_page'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'about.html')

    def test_contact_page_loads(self):
        response = self.client.get(reverse('contact_page'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'contact.html')

    def test_html_registration_student(self):
        post_data = {
            "email": "teststudent@shiftly.com",
            "role": "student",
            "first_name": "Sarah",
            "last_name": "Smith",
            "password": "strongpassword123",
            "confirm_password": "strongpassword123"
        }
        response = self.client.post(reverse('register_page'), post_data)
        # Check redirection to student dashboard
        self.assertRedirects(response, reverse('student_dashboard'))
        
        # Check user and student profile creation
        user = self.user_model.objects.get(email="teststudent@shiftly.com")
        self.assertEqual(user.role, "student")
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())
        self.assertEqual(user.student_profile.first_name, "Sarah")

    def test_html_registration_business(self):
        post_data = {
            "email": "testbusiness@shiftly.com",
            "role": "business",
            "company_name": "Red Coffee Corp",
            "password": "strongpassword123",
            "confirm_password": "strongpassword123"
        }
        response = self.client.post(reverse('register_page'), post_data)
        # Pending businesses should be redirected to login after submission
        self.assertRedirects(response, reverse('login_page'))
        
        # Check user and business profile creation
        user = self.user_model.objects.get(email="testbusiness@shiftly.com")
        self.assertEqual(user.role, "business")
        self.assertTrue(BusinessProfile.objects.filter(user=user).exists())
        self.assertEqual(user.business_profile.company_name, "Red Coffee Corp")
        self.assertEqual(user.status, self.user_model.AccountStatus.PENDING)
        self.assertFalse(user.is_active)

    def test_html_login_redirect_student(self):
        # Create user first
        user = self.user_model.objects.create_user(
            email="sarah@shiftly.com",
            password="strongpassword123",
            role="student"
        )
        StudentProfile.objects.create(user=user, first_name="Sarah", last_name="Smith")

        # Login
        post_data = {
            "email": "sarah@shiftly.com",
            "password": "strongpassword123"
        }
        response = self.client.post(reverse('login_page'), post_data)
        self.assertRedirects(response, reverse('student_dashboard'))

    def test_html_login_redirect_business(self):
        # Create an approved business user first
        user = self.user_model.objects.create_user(
            email="redcoffee@shiftly.com",
            password="strongpassword123",
            role="business",
            status=self.user_model.AccountStatus.APPROVED,
            is_active=True
        )
        BusinessProfile.objects.create(user=user, company_name="Red Coffee")

        # Login
        post_data = {
            "email": "redcoffee@shiftly.com",
            "password": "strongpassword123"
        }
        response = self.client.post(reverse('login_page'), post_data)
        self.assertRedirects(response, reverse('business_dashboard'))

    def test_html_logout_destroys_session(self):
        user = self.user_model.objects.create_user(
            email="testuser@shiftly.com",
            password="strongpassword123",
            role="student"
        )
        StudentProfile.objects.create(user=user, first_name="Sarah", last_name="Smith")

        self.client.login(email="testuser@shiftly.com", password="strongpassword123")
        response = self.client.get(reverse('logout_page'))
        self.assertRedirects(response, reverse('landing'))
        
        # Verify user is logged out (dashboard requires login redirect to /login/ with ?next=...)
        dashboard_response = self.client.get(reverse('student_dashboard'))
        self.assertRedirects(dashboard_response, f"{reverse('login_page')}?next={reverse('student_dashboard')}")

