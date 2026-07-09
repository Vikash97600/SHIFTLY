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
            "company_name": "Acme Corp",
            "owner_name": "John Doe",
            "mobile_number": "+1 (555) 019-2834",
            "address": "123 Main St",
            "business_category": "Food Services"
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

    def test_business_registration_duplicate_gst_number(self):
        """
        Verify that registering two business owners with the same GST number
        is rejected with a validation error on the API endpoint.
        """
        business_data_1 = self.business_data.copy()
        business_data_1["gst_number"] = "GSTIN753159824"
        response_1 = self.client.post(self.register_url, business_data_1, format='json')
        self.assertEqual(response_1.status_code, status.HTTP_201_CREATED)

        business_data_2 = self.business_data.copy()
        business_data_2["email"] = "business_diff@shiftly.com"
        business_data_2["gst_number"] = "GSTIN753159824"
        response_2 = self.client.post(self.register_url, business_data_2, format='json')
        
        self.assertEqual(response_2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("gst_number", response_2.data)

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
        
        profile = business_user.business_profile
        profile.status = 'APPROVED'
        profile.save()

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
            "owner_name": "Sarah Smith",
            "mobile_number": "+1 (555) 019-2834",
            "address": "123 Main St",
            "business_category": "Food Services",
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

    def test_html_registration_business_duplicate_gst_number(self):
        """
        Verify that registering a business owner via HTML page with a duplicate GST
        number displays an error on the form.
        """
        # Register first business via HTML
        post_data_1 = {
            "email": "testbusiness1@shiftly.com",
            "role": "business",
            "company_name": "Red Coffee Corp 1",
            "owner_name": "Sarah Smith",
            "mobile_number": "+1 (555) 019-2834",
            "address": "123 Main St",
            "business_category": "Food Services",
            "gst_number": "GSTIN753159824",
            "password": "strongpassword123",
            "confirm_password": "strongpassword123"
        }
        response_1 = self.client.post(reverse('register_page'), post_data_1)
        self.assertRedirects(response_1, reverse('login_page'))

        # Register second business with same GST number via HTML
        post_data_2 = {
            "email": "testbusiness2@shiftly.com",
            "role": "business",
            "company_name": "Red Coffee Corp 2",
            "owner_name": "Sarah Smith",
            "mobile_number": "+1 (555) 019-2834",
            "address": "123 Main St",
            "business_category": "Food Services",
            "gst_number": "GSTIN753159824",
            "password": "strongpassword123",
            "confirm_password": "strongpassword123"
        }
        response_2 = self.client.post(reverse('register_page'), post_data_2)
        
        # It should not redirect because of validation error (should stay on the page and show error)
        self.assertEqual(response_2.status_code, 200)
        self.assertTemplateUsed(response_2, 'register.html')
        self.assertFormError(response_2, 'form', 'gst_number', "A business with this GST number is already registered.")

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
        BusinessProfile.objects.create(user=user, company_name="Red Coffee", status='APPROVED')

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


from django.test import TestCase, Client
from accounts.models import UserQuery, QueryMessage

class UserQueryTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.student_user = User.objects.create_user(
            email="student@queries.com",
            password="testpass123",
            role="student"
        )
        StudentProfile.objects.create(
            user=self.student_user,
            first_name="Query",
            last_name="Tester"
        )

        self.admin_user = User.objects.create_user(
            email="admin@queries.com",
            password="testpass123",
            role="admin",
            is_staff=True
        )

    def test_contact_form_creates_userquery_linked_to_user(self):
        """
        Submitting the contact form with a registered email should
        create a UserQuery linked to that user account.
        """
        response = self.client.post(reverse('contact_page'), {
            'name': 'Query Tester',
            'email': 'student@queries.com',
            'subject': 'Wallet query',
            'message': 'How do I withdraw earnings?',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserQuery.objects.filter(email='student@queries.com').exists())
        query = UserQuery.objects.get(email='student@queries.com')
        self.assertEqual(query.user, self.student_user)

    def test_contact_form_creates_anonymous_query_for_unregistered_email(self):
        """
        Contact form with an unknown email creates a query with no linked user.
        """
        response = self.client.post(reverse('contact_page'), {
            'name': 'Anonymous Person',
            'email': 'nobody@example.com',
            'subject': 'General question',
            'message': 'What is SHIFTLY?',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        query = UserQuery.objects.get(email='nobody@example.com')
        self.assertIsNone(query.user)

    def test_user_queries_list_requires_login(self):
        """
        Unauthenticated users are redirected away from the queries list.
        """
        response = self.client.get(reverse('user_queries'))
        self.assertEqual(response.status_code, 302)

    def test_user_queries_list_shows_own_queries(self):
        """
        Logged-in users can see their own queries.
        """
        query = UserQuery.objects.create(
            user=self.student_user,
            name='Query Tester',
            email='student@queries.com',
            subject='Badge query',
            message='How do badges work?'
        )
        self.client.login(email='student@queries.com', password='testpass123')
        response = self.client.get(reverse('user_queries'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(query, response.context['queries'])

    def test_user_can_post_reply_in_query_chat(self):
        """
        A logged-in user can post a reply message in the support chat.
        """
        query = UserQuery.objects.create(
            user=self.student_user,
            name='Query Tester',
            email='student@queries.com',
            subject='Earnings question',
            message='How are my earnings calculated?'
        )
        self.client.login(email='student@queries.com', password='testpass123')
        self.client.post(reverse('user_query_chat', args=[query.id]), {
            'message': 'Please clarify the platform fee.'
        })
        self.assertTrue(QueryMessage.objects.filter(query=query, sender=self.student_user).exists())

    def test_admin_can_view_all_queries(self):
        """
        Admin can view all user queries regardless of who submitted them.
        """
        UserQuery.objects.create(
            user=self.student_user,
            name='Query Tester',
            email='student@queries.com',
            subject='Test query',
            message='Test message'
        )
        self.client.login(email='admin@queries.com', password='testpass123')
        response = self.client.get(reverse('admin_queries'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['queries'].count(), 1)

    def test_admin_can_reply_to_query(self):
        """
        Admin can post a reply to a user query and it appears in the thread.
        """
        query = UserQuery.objects.create(
            user=self.student_user,
            name='Query Tester',
            email='student@queries.com',
            subject='Admin reply test',
            message='Need help!'
        )
        self.client.login(email='admin@queries.com', password='testpass123')
        self.client.post(reverse('admin_query_chat', args=[query.id]), {
            'message': 'We are looking into this for you!'
        })
        self.assertTrue(
            QueryMessage.objects.filter(
                query=query,
                sender=self.admin_user,
                message='We are looking into this for you!'
            ).exists()
        )

    def test_admin_can_mark_query_resolved(self):
        """
        Submitting the resolve button sets the query to resolved.
        """
        query = UserQuery.objects.create(
            user=self.student_user,
            name='Query Tester',
            email='student@queries.com',
            subject='Resolve test',
            message='Please resolve this!'
        )
        self.client.login(email='admin@queries.com', password='testpass123')
        self.client.post(reverse('admin_query_chat', args=[query.id]), {
            'message': '',
            'resolve': '1'
        })
        query.refresh_from_db()
        self.assertTrue(query.is_resolved)
