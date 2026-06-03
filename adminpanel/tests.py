from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from accounts.models import Verification
from businesses.models import BusinessProfile, Earning
from students.models import StudentProfile
from jobs.models import JobPosting
from matches.models import Match, JobApplication
from reports.models import Report
from adminpanel.models import AuditLog

User = get_user_model()

class AdminPanelTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Admin User
        self.admin_user = User.objects.create_user(
            email="admin@shiftly.com",
            password="password123",
            role="admin",
            is_staff=True
        )

        # 2. Student User
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

        # 3. Business User
        self.business_user = User.objects.create_user(
            email="employer@shiftly.com",
            password="password123",
            role="business"
        )
        self.business_profile = BusinessProfile.objects.create(
            user=self.business_user,
            company_name="Red Coffee",
            industry="Food Services",
            business_registration_no="REG-RED123"
        )

        # 4. Job Posting
        self.job = JobPosting.objects.create(
            business=self.business_profile,
            title="Helper Barista",
            description="Short shift",
            location_name="Downtown SF",
            latitude=37.7749,
            longitude=-122.4194,
            base_pay=15.00,
            start_date=timezone.now().date() + timezone.timedelta(days=2),
            end_date=timezone.now().date() + timezone.timedelta(days=2),
            shift_start_time="08:00:00",
            shift_end_time="16:00:00",
            status="active"
        )

        # 5. Match
        self.match = Match.objects.create(
            student=self.student_profile,
            job=self.job,
            status='active'
        )

        # 6. Escrow Earning
        self.earning = Earning.objects.create(
            student=self.student_profile,
            business=self.business_profile,
            job=self.job,
            gross_amount=Decimal('120.00'),
            platform_fee=Decimal('12.00'),
            net_amount=Decimal('108.00'),
            payment_status='released',
            transaction_reference='TXN-TESTREV12'
        )

        # 7. Verification Request
        self.verification = Verification.objects.create(
            user=self.business_user,
            document_type=Verification.DocumentType.BUSINESS_LICENSE,
            document_url="https://s3.amazonaws.com/license.pdf",
            status='pending'
        )

        # 8. Abuse Report
        self.report = Report.objects.create(
            reporter=self.student_user,
            reported_job=self.job,
            reason_category="spam",
            description="Suspicious spam post",
            status='pending'
        )

    def test_admin_dashboard_role_guards(self):
        """
        Verify that only administrators can access the admin panel views.
        """
        url = reverse('admin_dashboard')

        # 1. Anonymous -> redirects (302)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # 2. Student user -> Forbidden (403)
        self.client.login(email="student@shiftly.com", password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # 3. Admin user -> Success (200)
        self.client.login(email="admin@shiftly.com", password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_kpis_calculation(self):
        """
        Verify that admin panel dashboard calculates KPIs correctly.
        """
        self.client.login(email="admin@shiftly.com", password="password123")
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)

        # Assert correct count metrics are loaded in template context
        self.assertEqual(response.context['total_users'], 3) # Admin, Student, Business
        self.assertEqual(response.context['active_jobs'], 1)
        self.assertEqual(response.context['total_businesses'], 1)
        self.assertEqual(response.context['total_matches'], 1)
        self.assertEqual(response.context['total_revenue'], Decimal('12.00'))

    def test_ajax_toggle_user_active(self):
        """
        Verify AJAX toggle of user active state.
        """
        self.client.login(email="admin@shiftly.com", password="password123")
        toggle_url = reverse('admin_toggle_user', args=[self.student_user.id])
        
        # Action -> toggle active status to False
        response = self.client.post(toggle_url, {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_active'])

        self.student_user.refresh_from_db()
        self.assertFalse(self.student_user.is_active)

        # Verify audit logging
        self.assertTrue(AuditLog.objects.filter(action='toggle_user_status', target_id=self.student_user.id).exists())

    def test_ajax_verify_approval_action(self):
        """
        Verify AJAX verification action approvals and updates.
        """
        self.client.login(email="admin@shiftly.com", password="password123")
        action_url = reverse('admin_verification_action', args=[self.verification.id])

        # Action -> Approve Verification
        response = self.client.post(action_url, {
            'status': 'approved'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'approved')

        # Verify profile is updated
        self.business_profile.refresh_from_db()
        self.assertEqual(self.business_profile.verification_status, 'verified')

        # Verify audit log
        self.assertTrue(AuditLog.objects.filter(action='verification_approved', target_id=self.verification.id).exists())

    def test_ajax_job_moderation_delete(self):
        """
        Verify AJAX job moderation deletions.
        """
        self.client.login(email="admin@shiftly.com", password="password123")
        action_url = reverse('admin_job_action', args=[self.job.id])

        # Action -> Delete job posting
        response = self.client.post(action_url, {
            'action': 'delete'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'deleted')

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'deleted')

        # Verify audit log
        self.assertTrue(AuditLog.objects.filter(action='job_delete', target_id=self.job.id).exists())

    def test_ajax_report_resolve(self):
        """
        Verify AJAX flagging report resolutions.
        """
        self.client.login(email="admin@shiftly.com", password="password123")
        action_url = reverse('admin_report_action', args=[self.report.id])

        # Action -> Resolve report
        response = self.client.post(action_url, {
            'action': 'resolve',
            'notes': 'Spam post removed'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'resolved')

        self.report.refresh_from_db()
        self.assertEqual(self.report.status, Report.ReportStatus.RESOLVED)
        self.assertEqual(self.report.resolution_action, 'Spam post removed')
        self.assertEqual(self.report.resolver, self.admin_user)

        # Verify audit log
        self.assertTrue(AuditLog.objects.filter(action='report_resolve', target_id=self.report.id).exists())
